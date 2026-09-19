#!/usr/bin/env python3
"""
gltf_validator.py — Validação rápida de GLB/GLTF para o pipeline.

Uso:
    python tools/python/gltf_validator.py --input out.glb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def validate(path: Path) -> dict:
    try:
        import gltflib
    except ImportError:
        return {"valid": False, "error": "gltflib não instalado (pip install gltflib)"}

    if not path.exists():
        return {"valid": False, "error": f"arquivo não encontrado: {path}"}

    gltf = gltflib.GLTF.load(str(path))

    polycount = 0
    for mesh in gltf.meshes:
        for prim in mesh.primitives:
            if prim.indices:
                polycount += prim.indices.count // 3

    warnings = []
    if polycount > 500_000:
        warnings.append(f"polycount alto: {polycount} (>500k)")

    if not gltf.meshes:
        warnings.append("nenhuma mesh encontrada")

    if not gltf.materials and not gltf.textures:
        warnings.append("nenhum material/textura — asset pode parecer básico")

    return {
        "valid": True,
        "file": str(path),
        "size_bytes": path.stat().st_size,
        "polycount": polycount,
        "meshes": len(gltf.meshes),
        "materials": len(gltf.materials),
        "textures": len(gltf.textures),
        "animations": len(gltf.animations),
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validador GLTF/GLB.")
    parser.add_argument("--input", required=True, help="Arquivo GLB/GLTF")
    args = parser.parse_args()

    report = validate(Path(args.input))
    print(json.dumps(report, indent=2))
    return 0 if report.get("valid") else 2


if __name__ == "__main__":
    sys.exit(main())
