"""
render_preview.py — Render thumbnail de mesh 3D usando Blender.

Roda headless Blender, importa o mesh, posiciona câmera, renderiza PNG.

Uso:
    python tools/python/render_preview.py \
        --input scene.glb \
        --output preview.png \
        [--width 800 --height 600] \
        [--camera-angle 30 --camera-elevation 45] \
        [--samples 64]

Internamente invoca Blender com script _render_blender.py.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

BLENDER_BIN = "/workspace/tools/blender-4.2.5-linux-x64/blender"
BLENDER_SCRIPT_FILE = "/workspace/ai-3d-world-pipeline/tools/python/_render_blender.py"


def render(
    input_path: str,
    output_path: str,
    width: int = 800,
    height: int = 600,
    camera_angle: float = 30.0,
    camera_elevation: float = 35.0,
    samples: int = 64,
    engine: str = "BLENDER_EEVEE_NEXT",
    distance: float = None,
    prompt: str = "",
    timeout: int = 300,
) -> dict:
    """Render mesh preview using Blender."""
    input_obj = Path(input_path)
    output_obj = Path(output_path)
    output_obj.parent.mkdir(parents=True, exist_ok=True)

    if not input_obj.exists():
        return {"ok": False, "error": f"input not found: {input_path}"}

    args = [
        BLENDER_BIN,
        "--background",
        "--python", BLENDER_SCRIPT_FILE,
        "--",
        "--input", str(input_obj),
        "--output", str(output_obj),
        "--width", str(width),
        "--height", str(height),
        "--camera-angle", str(camera_angle),
        "--camera-elevation", str(camera_elevation),
        "--samples", str(samples),
        "--engine", engine,
    ]
    if distance is not None:
        args.extend(["--distance", str(distance)])
    if prompt:
        args.extend(["--prompt", prompt])

    print(f"[render_preview] blender -> {output_obj}")
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/workspace/ai-3d-world-pipeline",
        )
        ok = proc.returncode == 0 and output_obj.exists()
        return {
            "ok": ok,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-1500:],
            "stderr": proc.stderr[-1000:],
            "output_exists": output_obj.exists(),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s"}


def main():
    p = argparse.ArgumentParser(description="Render mesh preview via Blender")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=600)
    p.add_argument("--camera-angle", type=float, default=30.0)
    p.add_argument("--camera-elevation", type=float, default=35.0)
    p.add_argument("--samples", type=int, default=64)
    p.add_argument("--engine", default="BLENDER_EEVEE_NEXT")
    p.add_argument("--distance", type=float, default=None)
    p.add_argument("--prompt", default="", help="Tinting baseado em biome keywords")
    args = p.parse_args()

    result = render(
        args.input, args.output,
        width=args.width, height=args.height,
        camera_angle=args.camera_angle,
        camera_elevation=args.camera_elevation,
        samples=args.samples,
        engine=args.engine,
        distance=args.distance,
        prompt=args.prompt,
    )

    if result["ok"]:
        print(f"✓ render: {args.output}")
    else:
        print(f"✗ render failed: {result.get('error', 'unknown')}")
        if "stderr" in result:
            print(result["stderr"][-500:])
        sys.exit(1)


if __name__ == "__main__":
    main()