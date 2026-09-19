"""
gpu_gate.py — Wrapper-aware GPU check.

Inspirado em JustVugg/colibri (c/colibri.c:130-134):
  "GPU support is opt-in via COLI_CUDA=1. Default is dependency-free CPU."

Aqui cada wrapper GPU-required chama este gate antes de tentar rodar.
- Se gpu_tier=cpu → exit 2 com mensagem clara "skipping <tool> porque <motivo>"
- Se gpu_tier=cuda/rocm/metal → continua normal

Usado pelos wrappers LichtFeld, WorldGen, GameFactory-3A, etc.
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path

# Importa gpu_probe (irmão de pacote)
try:
    from .gpu_probe import detect, GPU_TIER
except ImportError:
    # Permite execução direta (sem ser módulo)
    sys.path.insert(0, str(Path(__file__).parent))
    from gpu_probe import detect, GPU_TIER


# Tools que genuinamente precisam de GPU (CPU mode é inviável ou inexistente)
GPU_REQUIRED_TOOLS = {
    "lichtfeld": "LichtFeld Studio 3DGS training — 100% CUDA. CPU mode inexistente.",
    "worldgen":  "WorldGen (ZiYang-xie) — PyTorch + CUDA. CPU mode treinaria por dias.",
    "gamefactory": "GameFactory-3A — depende de WorldGen + outras redes neurais.",
    "terraforge3d": "TerraForge3D — OpenCL/GPU node editor. CPU mode limitado.",
    "colmap_dense": "COLMAP dense MVS — tem CPU mode mas é 10x+ mais lento (inviável).",
}


# Tools que têm CPU fallback funcional
CPU_OK_TOOLS = {
    "colmap_sparse": "COLMAP SfM esparso — CPU viável, só mais lento.",
    "bycob_world": "Bycob/world — CPU-only por design.",
    "blender": "Blender — CPU OK.",
    "godot": "Godot — CPU OK.",
    "rsgeotools": "rsgeotools — CPU OK.",
    "terasology": "Terasology — CPU OK.",
    "opensplat": "OpenSplat — tem CPU mode (C++ libtorch CPU, ~100x mais lento).",
}


def check(tool_name: str, *, force: bool = False) -> tuple[bool, str]:
    """Verifica se um tool pode rodar no ambiente atual.

    Returns:
        (can_run, reason)
        can_run=True se pode executar; False se deve pular.
        reason é a justificativa em qualquer caso.
    """
    config = detect()

    # bypass explícito
    if force or os.environ.get("PIPELINE_FORCE_GPU", "0") == "1":
        return True, f"FORCE flag set — tentando mesmo assim (gpu_tier={config.gpu_tier})"

    if config.has_gpu:
        return True, f"GPU {config.gpu_tier} detectada ({config.vram_free_mb} MB livres)"

    # Sem GPU
    if tool_name in GPU_REQUIRED_TOOLS:
        return False, (
            f"GPU ausente. {GPU_REQUIRED_TOOLS[tool_name]} "
            f"Para rodar este stage, instale CUDA Toolkit + driver NVIDIA, "
            f"ou remova este stage do pipeline."
        )
    elif tool_name in CPU_OK_TOOLS:
        return True, f"GPU ausente, mas {tool_name} tem CPU fallback funcional."
    else:
        # Tool desconhecido: deixa passar (defensivo)
        return True, f"GPU ausente mas {tool_name} não está marcado como GPU-required."


def gate_or_die(tool_name: str, *, force: bool = False):
    """Verifica gate. Se falhar, exit 2 com mensagem clara."""
    can_run, reason = check(tool_name, force=force)
    print(json.dumps({
        "stage": tool_name,
        "gpu_check": "pass" if can_run else "skip",
        "reason": reason,
    }, indent=2))
    if not can_run:
        sys.exit(2)


if __name__ == "__main__":
    # CLI: python -m tools.colibri_patterns.gpu_gate <tool_name> [--force]
    tool = sys.argv[1] if len(sys.argv) > 1 else "lichtfeld"
    force = "--force" in sys.argv
    gate_or_die(tool, force=force)
