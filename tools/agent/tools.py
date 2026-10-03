"""
tools.py — Tool Registry que envolve os wrappers existentes.

Adapta JustVugg/colibri (defineTool JSON schema) pro nosso mundo:
- Para cada wrapper em tools/cli-wrappers/ cria uma Tool com schema
- Para cada módulo Python em tools/python/ cria uma Tool com schema
- Mantém referencia ao pipeline_runner pra stages compostos

Inspirado em @deepseek-ai/dsh-tools (defineTool) mas em Python.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPERS_DIR = REPO_ROOT / "tools" / "cli-wrappers"
PYTHON_TOOLS_DIR = REPO_ROOT / "tools" / "python"
PIPELINES_DIR = REPO_ROOT / "pipelines"


@dataclass
class ToolParameter:
    """Schema JSON para um parâmetro."""
    type: str          # "string" | "integer" | "number" | "boolean" | "object" | "array"
    description: str
    enum: Optional[List[str]] = None
    default: Any = None
    required: bool = True


@dataclass
class Tool:
    """
    Definição de tool (estilo dsh-tools defineTool, em Python).

    Cada tool aponta pra um wrapper existente (.sh) ou módulo Python
    que JÁ EXISTE no repo. Não duplicamos implementação — só declaramos
    o schema pra LLM poder chamar.
    """
    name: str
    description: str
    parameters: Dict[str, ToolParameter] = field(default_factory=dict)
    category: str = "general"   # generation | processing | export | analysis | pipeline
    backend: str = "sh"         # sh | python | pipeline
    target: Optional[str] = None  # path do wrapper .sh ou módulo python
    gpu_required: bool = False
    timeout_s: int = 600

    def to_json_schema(self) -> Dict[str, Any]:
        """Converte pra OpenAI/DeepSeek function calling schema."""
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for pname, p in self.parameters.items():
            prop: Dict[str, Any] = {"type": p.type}
            if p.description:
                prop["description"] = p.description
            if p.enum:
                prop["enum"] = p.enum
            if p.default is not None:
                prop["default"] = p.default
            properties[pname] = prop
            if p.required:
                required.append(pname)
        schema = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    def to_openai_tool(self) -> Dict[str, Any]:
        """Formato OpenAI/DeepSeek tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.to_json_schema(),
            },
        }

    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o tool (wrapper .sh OU módulo python OU pipeline)."""
        if self.backend == "sh":
            return self._execute_sh(args)
        elif self.backend == "python":
            return self._execute_python(args)
        elif self.backend == "pipeline":
            return self._execute_pipeline(args)
        raise ValueError(f"Unknown backend: {self.backend}")

    def _execute_sh(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self.target:
            raise ValueError(f"Tool {self.name} has no .sh target")
        wrapper_path = Path(self.target)
        if not wrapper_path.exists():
            return {"ok": False, "error": f"wrapper not found: {wrapper_path}"}

        cmd = ["bash", str(wrapper_path)]
        for k, v in args.items():
            if isinstance(v, bool):
                if v:
                    cmd.append(f"--{k.replace('_', '-')}")
            elif isinstance(v, (list, tuple)):
                cmd.extend([f"--{k.replace('_', '-')}", ",".join(map(str, v))])
            else:
                cmd.extend([f"--{k.replace('_', '-')}", str(v)])

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout_s, cwd=REPO_ROOT,
            )
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-4000:],   # tail pra não estourar
                "stderr": proc.stderr[-2000:],
                "command": " ".join(cmd),
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout after {self.timeout_s}s"}

    def _execute_python(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self.target:
            raise ValueError(f"Tool {self.name} has no python target")
        module = self.target  # formato "tools.python.<name>"
        cmd = ["python3", "-m", module]
        for k, v in args.items():
            if isinstance(v, bool):
                if v:
                    cmd.append(f"--{k.replace('_', '-')}")
            elif isinstance(v, (list, tuple)):
                cmd.extend([f"--{k.replace('_', '-')}", ",".join(map(str, v))])
            else:
                cmd.extend([f"--{k.replace('_', '-')}", str(v)])

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout_s, cwd=REPO_ROOT,
            )
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-2000:],
                "command": " ".join(cmd),
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout after {self.timeout_s}s"}

    def _execute_pipeline(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self.target:
            raise ValueError(f"Tool {self.name} has no pipeline target")
        # Pipeline = YAML existente em pipelines/, roda via pipeline_runner.py
        cmd = ["python3", str(PYTHON_TOOLS_DIR / "pipeline_runner.py"),
               "--pipeline", self.target]
        for k, v in args.items():
            cmd.extend([f"--var", f"{k}={v}"])

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout_s, cwd=REPO_ROOT,
            )
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-2000:],
                "command": " ".join(cmd),
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout after {self.timeout_s}s"}


class ToolRegistry:
    """Registry de tools — dsh-tools em Python."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self.register_defaults()

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def categories(self) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for t in self._tools.values():
            out.setdefault(t.category, []).append(t.name)
        return out

    def as_openai_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.category == category]
        return [t.to_openai_tool() for t in tools]

    def register_defaults(self):
        """Registra todas as tools padrão baseadas nos wrappers existentes."""
        # ============ WRAPPERS .sh ============
        self.register(Tool(
            name="bycob_world",
            description="Gera mundo procedural com Bycob/world (C++). Tipos: terrain, tree, mapper. Retorna .obj + .png.",
            parameters={
                "test": ToolParameter("string", "Tipo de asset a gerar", enum=["terrain", "tree", "mapper"], default="terrain"),
                "output": ToolParameter("string", "Diretório de saída (--output)", required=False, default="./bycob_out"),
                "seed": ToolParameter("integer", "Seed aleatório (--seed)", required=False, default=42),
                "terrain": ToolParameter("boolean", "Inclui terrain mesh", required=False, default=True),
                "vegetation": ToolParameter("boolean", "Inclui vegetation/trees", required=False, default=True),
            },
            category="generation",
            backend="sh",
            target=str(WRAPPERS_DIR / "bycob_world.sh"),
            timeout_s=300,
        ))

        self.register(Tool(
            name="blender_process",
            description="Processa mesh 3D via Blender (OBJ→GLB com LODs, decimação, colliders).",
            parameters={
                "input": ToolParameter("string", "Arquivo de entrada (.obj, .glb)"),
                "output": ToolParameter("string", "Arquivo de saída (.glb)"),
                "max_tris": ToolParameter("integer", "Máximo de triângulos", required=False, default=30000),
                "lod_levels": ToolParameter("integer", "Níveis de LOD", required=False, default=3),
                "collider": ToolParameter("string", "Tipo de collider", enum=["trimesh", "convex", "none"], required=False, default="trimesh"),
            },
            category="processing",
            backend="sh",
            target=str(WRAPPERS_DIR / "blender_process.sh"),
            timeout_s=120,
        ))

        self.register(Tool(
            name="cubiquity_generate",
            description="Gera voxel world procedural com Cubiquity (C++). Algoritmos: menger_sponge, fractal_noise, worley_noise, checkerboard. Retorna slices PNG + arquivo .dag.",
            parameters={
                "algorithm": ToolParameter("string", "Algoritmo procedural", enum=["menger_sponge", "fractal_noise", "worley_noise", "checkerboard"]),
                "size": ToolParameter("integer", "Tamanho em voxels por eixo (8-256)", default=64),
                "output-dir": ToolParameter("string", "Diretório ABSOLUTO de saída (--output-dir)", required=False, default="/workspace/ai-3d-world-pipeline/outputs/cubiquity_default"),
            },
            category="generation",
            backend="sh",
            target=str(WRAPPERS_DIR / "cubiquity_demo.sh"),
            timeout_s=120,
        ))

        self.register(Tool(
            name="colmap_reconstruct",
            description="Photogrammetry SfM+MVS via COLMAP. Reconstroi cena 3D de fotos.",
            parameters={
                "images_dir": ToolParameter("string", "Diretório com fotos de entrada"),
                "output_dir": ToolParameter("string", "Diretório de saída"),
                "gpu": ToolParameter("boolean", "Usar GPU (false=CPU only)", required=False, default=False),
            },
            category="reconstruction",
            backend="sh",
            target=str(WRAPPERS_DIR / "colmap.sh"),
            gpu_required=False,
            timeout_s=3600,
        ))

        self.register(Tool(
            name="opensplat_train",
            description="Treina 3D Gaussian Splatting em CPU. Input: imagens + cameras COLMAP-style.",
            parameters={
                "input_dir": ToolParameter("string", "Diretório com cameras.txt + images"),
                "output": ToolParameter("string", "Arquivo .ply de saída"),
                "iterations": ToolParameter("integer", "Iterações de treino", required=False, default=7000),
            },
            category="reconstruction",
            backend="sh",
            target=str(WRAPPERS_DIR / "opensplat_train.sh"),
            timeout_s=3600,
        ))

        self.register(Tool(
            name="rsgeotools_generate",
            description="Gera cidade 3D a partir de tile OSM (rsgeotools-rvtgen3d).",
            parameters={
                "tile_x": ToolParameter("integer", "Coordenada X do tile OSM"),
                "tile_y": ToolParameter("integer", "Coordenada Y do tile OSM"),
                "output": ToolParameter("string", "Arquivo de saída (.obj ou .glb)"),
            },
            category="generation",
            backend="sh",
            target=str(WRAPPERS_DIR / "rsgeotools.sh"),
            timeout_s=120,
        ))

        self.register(Tool(
            name="terraforge",
            description="Editor de terreno GUI (TerraForge3D 2.3, requer xvfb).",
            parameters={
                "terrain_file": ToolParameter("string", "Arquivo .obj de terreno"),
                "output": ToolParameter("string", "Terreno modificado"),
            },
            category="processing",
            backend="sh",
            target=str(WRAPPERS_DIR / "terraforge.sh"),
            timeout_s=300,
        ))

        # ============ MÓDULOS PYTHON ============
        self.register(Tool(
            name="gltf_validate",
            description="Valida arquivo GLB/glTF (checha schema, meshes, materials).",
            parameters={
                "input": ToolParameter("string", "Arquivo .glb ou .gltf"),
            },
            category="analysis",
            backend="python",
            target="tools.python.gltf_validator",
            timeout_s=30,
        ))

        self.register(Tool(
            name="libigl_analyze",
            description="Analisa mesh com libigl: vértices, faces, área, curvatura gaussiana, boundary loops.",
            parameters={
                "input": ToolParameter("string", "Arquivo .obj de entrada"),
                "output": ToolParameter("string", "Arquivo .obj de saída (opcional)", required=False),
            },
            category="analysis",
            backend="python",
            target="tools.python.libigl_mesh_analysis",
            timeout_s=60,
        ))

        self.register(Tool(
            name="godot_build_scene",
            description="Cria projeto Godot 4 completo (jogo jogável) a partir de GLB. Gera project.godot, scripts/player.gd (WASD+space+mouse look), assets/world.glb.",
            parameters={
                "glb": ToolParameter("string", "Caminho ABSOLUTO do arquivo .glb do mundo (--glb)"),
                "output": ToolParameter("string", "Caminho do diretório ABSOLUTO do projeto Godot (--output)"),
            },
            category="export",
            backend="python",
            target="tools.python.create_game_scene",
            timeout_s=30,
        ))

        self.register(Tool(
            name="worldgen_lite_i2mesh",
            description="WorldGen-Lite (ZiYang-xie/WorldGen CPU-compatible): converte panorama equirectangular em mesh 3D (.ply/.obj). Skip FLUX (gated), usa depth heuristic + Poisson reconstruction.",
            parameters={
                "input": ToolParameter("string", "Panorama equirectangular 2:1 (jpg/png)"),
                "output": ToolParameter("string", "Arquivo .ply de saída"),
                "obj": ToolParameter("string", "Também exportar .obj (--obj)", required=False),
                "method": ToolParameter("string", "Reconstruction method", enum=["poisson", "ball_pivoting", "alpha_shape"], required=False, default="poisson"),
                "downscale": ToolParameter("integer", "Fator de redução (default 8)", required=False, default=8),
                "far": ToolParameter("number", "Distância máxima (metros)", required=False, default=100.0),
                "near": ToolParameter("number", "Distância mínima (metros)", required=False, default=0.5),
            },
            category="generation",
            backend="sh",
            target=str(WRAPPERS_DIR / "worldgen_lite_i2mesh.sh"),
            timeout_s=300,
        ))

        self.register(Tool(
            name="worldgen_lite_t2mesh",
            description="WorldGen-Lite: text prompt → mesh 3D. Se HF_TOKEN fornecido usa FLUX.1-dev real (gated). Senão gera panorama procedural baseada em keywords (snow/forest/mountain/city/etc).",
            parameters={
                "prompt": ToolParameter("string", "Text prompt descrevendo a cena"),
                "output": ToolParameter("string", "Arquivo .ply de saída"),
                "obj": ToolParameter("string", "Também exportar .obj", required=False),
                "method": ToolParameter("string", "Reconstruction", enum=["poisson", "ball_pivoting", "alpha_shape"], required=False, default="poisson"),
                "downscale": ToolParameter("integer", "Fator de redução", required=False, default=8),
                "resolution": ToolParameter("integer", "Resolução panorama (largura)", required=False, default=1024),
                "hf-token": ToolParameter("string", "HF token para FLUX real (opcional)", required=False),
                "fallback-procedural": ToolParameter("boolean", "Permitir fallback procedural", required=False, default=True),
            },
            category="generation",
            backend="sh",
            target=str(WRAPPERS_DIR / "worldgen_lite_t2mesh.sh"),
            timeout_s=600,
        ))

        self.register(Tool(
            name="asset_processor",
            description="Pipeline Python para processar assets 3D (OBJ/GLB) com LODs. Aceita --input, --output, --max-tris, --lod-levels, --collider.",
            parameters={
                "input": ToolParameter("string", "Caminho ABSOLUTO do arquivo de entrada (.obj ou .glb)"),
                "output": ToolParameter("string", "Caminho ABSOLUTO do arquivo de saída (.glb)"),
                "max_tris": ToolParameter("integer", "Máx triângulos", required=False, default=50000),
                "lod_levels": ToolParameter("integer", "Níveis LOD", required=False, default=3),
                "collider": ToolParameter("string", "Tipo de collider (trimesh|convex|none)", enum=["trimesh", "convex", "none"], required=False, default="trimesh"),
            },
            category="processing",
            backend="python",
            target="tools.python.asset_processor",
            timeout_s=120,
        ))

        # ============ PIPELINES COMPOSTAS ============
        for pipeline_file in PIPELINES_DIR.glob("*.yaml"):
            name = f"pipeline_{pipeline_file.stem}"
            self.register(Tool(
                name=name,
                description=f"Roda pipeline composta: {pipeline_file.stem}. Veja {pipeline_file.name}.",
                parameters={
                    "output_dir": ToolParameter("string", "Diretório de saída", required=False, default="./outputs/" + pipeline_file.stem),
                },
                category="pipeline",
                backend="pipeline",
                target=str(pipeline_file),
                timeout_s=1800,
            ))


if __name__ == "__main__":
    # Self-test: lista todas as tools registradas
    reg = ToolRegistry()
    print(f"Total tools: {len(reg.all())}\n")
    for cat, names in reg.categories().items():
        print(f"[{cat}] ({len(names)})")
        for n in names:
            print(f"  - {n}")
