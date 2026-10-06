"""
generate_game.py — Pipeline "3A" pra criar asset pack + projeto Godot.

Inspirado em "GameFactory-3A" (gera assets AAA-like de texto). Como nosso:
- text prompt → worldgen_lite (panorama → mesh)
- + cubiquity (voxel decoration)
- + bycob (trees/details)
- + Blender (LODs)
- + Godot (game-ready scene)

Uso:
    python3 -m tools.gamefactory_3a.generate_game \
        --prompt "cozy medieval village" \
        --output /workspace/game/village \
        [--include-voxel] [--include-trees] [--include-lod]

Implementa o que GameFactory-3A propõe:
- to_scene: gera mesh + materiais + assets pra um engine
- to_engine: adapta pro engine alvo (Godot por default)

Adapta de worldgen_lite (substitui FLUX/DA-2 por procedural + Poisson)
e adiciona camadas de detalhe (voxel decoration, tree scattering).
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list, cwd: str = None, timeout: int = 600, log_path: str = None) -> dict:
    """Run command and capture result."""
    print(f"[gamefactory] $ {' '.join(cmd)}")
    log_path_obj = open(log_path, "a") if log_path else None
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        if log_path_obj:
            log_path_obj.write(f"\n=== {' '.join(cmd)} ===\n")
            log_path_obj.write(proc.stdout)
            log_path_obj.write(proc.stderr)
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-3000:],
            "stderr": proc.stderr[-1500:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s"}
    finally:
        if log_path_obj:
            log_path_obj.close()


def step_worldgen(
    prompt: str,
    output_dir: Path,
    log_path: str,
    downscale: int = 16,
) -> Path:
    """Step 1: worldgen_lite → terrain/environment mesh."""
    print("\n=== STEP 1: WorldGen-Lite (text → panorama → mesh) ===")
    terrain_ply = output_dir / "terrain.ply"
    terrain_obj = output_dir / "terrain.obj"
    result = run(
        ["python3", "-m", "tools.worldgen_lite.t2mesh",
         "--prompt", prompt,
         "--output", str(terrain_ply),
         "--obj", str(terrain_obj),
         "--fallback-procedural",
         "--downscale", str(downscale)],
        cwd="/workspace/ai-3d-world-pipeline",
        timeout=600,
        log_path=log_path,
    )
    if not result["ok"]:
        print(f"  ERROR: {result.get('error', 'unknown')}")
        return None
    print(f"  ✓ terrain: {terrain_ply} ({terrain_ply.stat().st_size:,} bytes)")
    return terrain_obj if terrain_obj.exists() else terrain_ply


def step_bycob_decoration(
    output_dir: Path,
    log_path: str,
) -> Path:
    """Step 2a: Bycob → trees/instances (CPU-only)."""
    print("\n=== STEP 2a: Bycob (trees/details) ===")
    bycob_dir = output_dir / "bycob"
    bycob_dir.mkdir(exist_ok=True)
    # Direct bycob call (flags sem args: --terrain é toggle)
    result = run(
        ["bash", "/workspace/ai-3d-world-pipeline/tools/cli-wrappers/bycob_world.sh",
         "--test", "tree",
         "--output", str(bycob_dir),
         "--vegetation"],
        timeout=300,
        log_path=log_path,
    )
    if not result["ok"]:
        print(f"  ERROR: {result.get('error', 'unknown')}")
        print(f"  stderr: {result.get('stderr', '')[:300]}")
        return None
    tree_obj = bycob_dir / "tree" / "instances.obj"
    if tree_obj.exists():
        print(f"  ✓ trees: {tree_obj}")
        return tree_obj
    print(f"  WARN: bycob rodou mas {tree_obj} não existe")
    return None


def step_cubiquity_decoration(
    output_dir: Path,
    log_path: str,
    algorithm: str = "menger_sponge",
    size: int = 32,
) -> Path:
    """Step 2b: Cubiquity → voxel decoration."""
    print(f"\n=== STEP 2b: Cubiquity (algorithm={algorithm}, size={size}) ===")
    cub_dir = output_dir / "cubiquity"
    cub_dir.mkdir(exist_ok=True)
    result = run(
        ["python3", "-m", "tools.worldgen_lite.i2mesh", "--help"],   # placeholder
        log_path=log_path,
    )
    # Direct cubiquity call via wrapper
    result = run(
        ["bash", "/workspace/ai-3d-world-pipeline/tools/cli-wrappers/cubiquity_demo.sh",
         "--algorithm", algorithm,
         "--size", str(size),
         "--output-dir", str(cub_dir)],
        timeout=120,
        log_path=log_path,
    )
    if not result["ok"]:
        print(f"  ERROR: {result.get('error', 'unknown')}")
        return None
    voxel_dir = cub_dir / f"{algorithm.split('_')[0]}_pngs"
    if voxel_dir.exists():
        print(f"  ✓ voxel world: {voxel_dir}")
        return voxel_dir
    return None


def step_blender_process(
    input_path: Path,
    output_dir: Path,
    log_path: str,
    lod_levels: int = 3,
    max_tris: int = 30000,
) -> Path:
    """Step 3: Blender process mesh com LODs."""
    print("\n=== STEP 3: Blender (process to GLB with LODs) ===")
    out_glb = output_dir / "terrain.glb"
    blender_bin = "/workspace/tools/blender-4.2.5-linux-x64/blender"
    result = run(
        [blender_bin, "--background", "--python",
         "/workspace/ai-3d-world-pipeline/tools/python/asset_processor.py",
         "--",
         "--input", str(input_path),
         "--output", str(out_glb),
         "--max-tris", str(max_tris),
         "--lod-levels", str(lod_levels)],
        timeout=300,
        log_path=log_path,
    )
    if not result["ok"]:
        print(f"  ERROR: {result.get('error', 'unknown')}")
        print(f"  stderr: {result.get('stderr', '')[:300]}")
        return None
    if out_glb.exists():
        print(f"  ✓ GLB: {out_glb} ({out_glb.stat().st_size:,} bytes)")
        return out_glb
    print(f"  WARN: blender rodou mas {out_glb} não existe")
    return None


def step_gltf_validate(
    glb_path: Path,
    log_path: str,
) -> dict:
    """Step 4: Validate GLB."""
    print("\n=== STEP 4: gltf_validate ===")
    result = run(
        ["python3", "-m", "tools.python.gltf_validator",
         "--input", str(glb_path)],
        cwd="/workspace/ai-3d-world-pipeline",
        timeout=30,
        log_path=log_path,
    )
    print(f"  {'✓' if result['ok'] else '✗'} validation: {result['stdout'][-200:]}")
    return result


def step_render_previews(
    output_dir: Path,
    log_path: str,
    terrain_glb: Path = None,
    terrain_obj: Path = None,
    voxel_dir: Path = None,
    tree_obj: Path = None,
) -> list:
    """Step 5: Render PNG previews de todos os assets."""
    print("\n=== STEP 5: Render previews ===")
    previews_dir = output_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    # Render terrain
    if terrain_glb and terrain_glb.exists():
        out = previews_dir / "terrain.png"
        result = run(
            ["python3", "-m", "tools.python.render_preview",
             "--input", str(terrain_glb),
             "--output", str(out),
             "--width", "800", "--height", "600",
             "--samples", "32", "--camera-angle", "30", "--camera-elevation", "35",
             "--prompt", output_dir.parent.name if False else ""],
            cwd="/workspace/ai-3d-world-pipeline",
            timeout=300,
            log_path=log_path,
        )
        if result["ok"]:
            print(f"  ✓ terrain preview: {out}")
            generated.append(out)
        else:
            print(f"  ✗ terrain preview failed: {result.get('error', result.get('stderr', '')[:200])}")

    # Render trees
    if tree_obj and tree_obj.exists():
        out = previews_dir / "trees.png"
        result = run(
            ["python3", "-m", "tools.python.render_preview",
             "--input", str(tree_obj),
             "--output", str(out),
             "--width", "600", "--height", "600",
             "--samples", "24", "--camera-angle", "45", "--camera-elevation", "60"],
            cwd="/workspace/ai-3d-world-pipeline",
            timeout=300,
            log_path=log_path,
        )
        if result["ok"]:
            print(f"  ✓ trees preview: {out}")
            generated.append(out)
        else:
            print(f"  ✗ trees preview failed: {result.get('error', result.get('stderr', '')[:200])}")

    # Composite panorama preview (já gerado pelo procedural_pano)
    if (output_dir / "terrain.ply").exists():
        # Compor panorama image a partir do OBJ
        pass

    return generated


def step_godot_build_scene(
    glb_path: Path,
    godot_dir: Path,
    log_path: str,
    scene_name: str = "Generated World",
) -> Path:
    """Step 5: Build Godot 4 game project."""
    print("\n=== STEP 5: godot_build_scene ===")
    godot_dir.mkdir(parents=True, exist_ok=True)
    result = run(
        ["python3", "-m", "tools.python.create_game_scene",
         "--glb", str(glb_path),
         "--output", str(godot_dir)],
        cwd="/workspace/ai-3d-world-pipeline",
        timeout=60,
        log_path=log_path,
    )
    if not result["ok"]:
        print(f"  ERROR: {result.get('error', 'unknown')}")
        return None
    print(f"  ✓ Godot project: {godot_dir}")
    return godot_dir


def main():
    p = argparse.ArgumentParser(
        description="GameFactory-3A: gera asset pack + projeto Godot a partir de texto.",
    )
    p.add_argument("--prompt", required=True, help="Text prompt")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--scene-name", default="Generated World")
    p.add_argument("--include-voxel", action="store_true", default=True,
                   help="Inclui voxel decoration (Cubiquity)")
    p.add_argument("--include-trees", action="store_true", default=True,
                   help="Inclui trees/instances (Bycob)")
    p.add_argument("--include-lod", action="store_true", default=True,
                   help="Inclui LOD generation (Blender)")
    p.add_argument("--voxel-algo", default="menger_sponge",
                   choices=["menger_sponge", "fractal_noise", "worley_noise", "checkerboard"])
    p.add_argument("--voxel-size", type=int, default=32)
    p.add_argument("--downscale", type=int, default=16, help="WorldGen downscale")
    p.add_argument("--lod-levels", type=int, default=3)
    p.add_argument("--max-tris", type=int, default=30000)
    args = p.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "gamefactory.log"
    log_path.write_text(f"=== GameFactory-3A ===\nprompt: {args.prompt}\noutput: {output_dir}\n\n")

    print(f"\n🎮 GameFactory-3A: '{args.prompt}'")
    print(f"   output: {output_dir}")
    print(f"   log: {log_path}\n")

    # Step 1: WorldGen-Lite → terrain
    terrain_obj = step_worldgen(args.prompt, output_dir, str(log_path), args.downscale)
    if terrain_obj is None:
        print("\n❌ Step 1 (WorldGen) falhou")
        return 1

    # Step 2: Decorations
    if args.include_trees:
        tree_obj = step_bycob_decoration(output_dir, str(log_path))
    if args.include_voxel:
        voxel_dir = step_cubiquity_decoration(
            output_dir, str(log_path),
            algorithm=args.voxel_algo, size=args.voxel_size,
        )

    # Step 3: Blender → GLB (optional)
    glb_path = None
    if args.include_lod and terrain_obj and terrain_obj.exists():
        glb_path = step_blender_process(
            terrain_obj, output_dir, str(log_path),
            lod_levels=args.lod_levels, max_tris=args.max_tris,
        )

    # Step 4: Validate GLB
    if glb_path and glb_path.exists():
        step_gltf_validate(glb_path, str(log_path))

    # Step 5: Render previews PNG (terrain + trees)
    tree_path = output_dir / "bycob" / "tree" / "instances.obj"
    previews = step_render_previews(
        output_dir, str(log_path),
        terrain_glb=glb_path, terrain_obj=terrain_obj,
        voxel_dir=voxel_dir, tree_obj=tree_path if tree_path.exists() else None,
    )

    # Step 6: Godot project
    if glb_path and glb_path.exists():
        godot_dir = output_dir / "godot_project"
        step_godot_build_scene(glb_path, godot_dir, str(log_path), args.scene_name)

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ GameFactory-3A completo!")
    print(f"{'='*60}")
    print(f"Output dir: {output_dir}")
    print(f"\nConteúdo gerado:")
    # Limita listagem pra 30 arquivos + previews destacados
    files = sorted(output_dir.rglob("*"))
    previews = []
    others = []
    for p in files:
        if p.is_file():
            if "preview" in str(p):
                previews.append(p)
            else:
                others.append(p)
    for p in previews[:10]:
        rel = p.relative_to(output_dir)
        size_kb = p.stat().st_size / 1024
        print(f"  📸 {rel} ({size_kb:.0f} KB)")
    if len(others) > 30:
        print(f"  ... +{len(others) - 30} outros arquivos")
        for p in others[:30]:
            rel = p.relative_to(output_dir)
            print(f"  📦 {rel}")
    else:
        for p in others:
            rel = p.relative_to(output_dir)
            print(f"  📦 {rel}")
    print(f"\nPróximos passos:")
    if (output_dir / "godot_project").exists():
        print(f"  godot --path {output_dir}/godot_project")
    if previews:
        print(f"  ver previews: ls {output_dir}/previews/")
    return 0


if __name__ == "__main__":
    sys.exit(main())