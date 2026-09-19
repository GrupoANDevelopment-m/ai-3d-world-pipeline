"""
cli.py — Entry point unificado (estilo ./coli do JustVugg/colibri).

Uso:
    python3 -m tools.colibri_patterns.cli info
    python3 -m tools.colibri_patterns.cli serve --port 8765
    python3 -m tools.colibri_patterns.cli gpu
    python3 -m tools.colibri_patterns.cli tier
    python3 -m tools.colibri_patterns.cli lease
    python3 -m tools.colibri_patterns.cli stream
    python3 -m tools.colibri_patterns.cli doctor
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_info(args):
    from .gpu_probe import detect
    cfg = detect()
    print("🐦 pipeline_gateway (inspired by JustVugg/colibri)")
    print(f"   GPU: {cfg.gpu_tier} (has_gpu={cfg.has_gpu})")
    print(f"   Policy: {cfg.recommended_policy}")
    print(f"   VRAM total: {cfg.vram_total_mb} MB")
    if cfg.notes:
        print(f"   Notes: {cfg.notes}")


def cmd_serve(args):
    from .pipeline_gateway import serve
    serve(args.host, args.port)


def cmd_gpu(args):
    from .gpu_probe import detect
    print(json.dumps(detect().to_dict(), indent=2))


def cmd_tier(args):
    from .tier_manager import demo
    demo()


def cmd_lease(args):
    from .asset_lease import main
    main()


def cmd_stream(args):
    from .asset_streamer import main
    main()


def cmd_doctor(args):
    """Health check do sistema inteiro (espelha ./coli doctor do Colibri)."""
    import shutil
    import subprocess
    print("🐦 pipeline doctor\n")

    checks = []

    # Python
    checks.append(("python3", shutil.which("python3") is not None, sys.version.split()[0]))

    # Git
    checks.append(("git", shutil.which("git") is not None, ""))

    # CMake (pra builds C++)
    cmake = shutil.which("cmake")
    checks.append(("cmake", cmake is not None, subprocess.run(["cmake", "--version"], capture_output=True, text=True).stdout.split("\n")[0] if cmake else ""))

    # JDK (Terasology)
    java = shutil.which("java")
    java_v = subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.split("\n")[0] if java else ""
    checks.append(("java", java is not None, java_v))

    # Blender (se instalado)
    blender_paths = [
        "/opt/tools/blender-4.2.5-linux-x64/blender",
        "/usr/local/bin/blender",
        "/usr/bin/blender",
    ]
    blender = next((p for p in blender_paths if Path(p).exists()), None)
    blender_v = subprocess.run([blender, "--version"], capture_output=True, text=True).stdout.split("\n")[0] if blender else ""
    checks.append(("blender", blender is not None, blender_v))

    # Godot
    godot_paths = ["/opt/tools/Godot_v4.3-stable_linux.x86_64", "/usr/local/bin/godot"]
    godot = next((p for p in godot_paths if Path(p).exists()), None)
    godot_v = subprocess.run([godot, "--version"], capture_output=True, text=True).stdout.strip() if godot else ""
    checks.append(("godot", godot is not None, godot_v))

    # Bycob
    bycob = Path("/opt/tools/world/build/bin")
    checks.append(("bycob_world (C++ build)", bycob.exists() and (bycob / "test_terrain").exists(),
                   f"binários: {len(list(bycob.glob('*'))) if bycob.exists() else 0}" if bycob.exists() else ""))

    # Colibri reference
    colibri = Path("/opt/tools/colibri/c/colibri")
    checks.append(("colibri (reference)", colibri.exists(), "v1.11.0 binary" if colibri.exists() else ""))

    # Python deps
    py_deps = ["yaml", "gltflib", "trimesh", "opensimplex", "PIL", "numpy", "cv2"]
    for dep in py_deps:
        try:
            __import__(dep)
            checks.append((f"python:{dep}", True, ""))
        except ImportError:
            checks.append((f"python:{dep}", False, "missing"))

    # GPU
    from .gpu_probe import detect
    gpu = detect()
    checks.append(("gpu", gpu.has_gpu, f"{gpu.gpu_tier} - {gpu.notes}"))

    # Print
    for name, ok, info in checks:
        sym = "✓" if ok else "✗"
        print(f"  [{sym}] {name:30s}  {info}")

    failed = sum(1 for _, ok, _ in checks if not ok)
    print(f"\n{len(checks) - failed}/{len(checks)} checks passed")
    return 0 if failed == 0 else 1


def main():
    p = argparse.ArgumentParser(prog="pipeline", description="AI 3D World Pipeline CLI (Colibri-inspired)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("info", help="Quick system info")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("serve", help="Start HTTP gateway")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8765)
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("gpu", help="Probe GPU")
    sp.set_defaults(func=cmd_gpu)

    sp = sub.add_parser("tier", help="Demo tier manager")
    sp.set_defaults(func=cmd_tier)

    sp = sub.add_parser("lease", help="Demo asset lease")
    sp.set_defaults(func=cmd_lease)

    sp = sub.add_parser("stream", help="Demo asset streamer")
    sp.set_defaults(func=cmd_stream)

    sp = sub.add_parser("doctor", help="Full system health check")
    sp.set_defaults(func=cmd_doctor)

    args = p.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
