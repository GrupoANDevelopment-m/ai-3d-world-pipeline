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

    # gltflib 1.x API: meshes/materials/textures are properties on the GLTF object.
    # Em algumas versões são accessors via .model — tenta ambos.
    try:
        meshes = gltf.meshes or []
    except AttributeError:
        try:
            meshes = gltf.model.meshes or []
        except AttributeError:
            meshes = []

    polycount = 0
    for mesh in meshes:
        try:
            primitives = mesh.primitives or []
        except AttributeError:
            primitives = []
        for prim in primitives:
            try:
                if prim.indices:
                    polycount += (prim.indices.count or 0) // 3
            except AttributeError:
                pass

    def _safe_len(attr):
        for owner in (gltf, getattr(gltf, "model", None)):
            if owner is None:
                continue
            try:
                v = getattr(owner, attr)
                return len(v) if v is not None else 0
            except AttributeError:
                continue
        return 0

    warnings = []
    if polycount > 500_000:
        warnings.append(f"polycount alto: {polycount} (>500k)")
    if not meshes:
        warnings.append("nenhuma mesh encontrada")
    materials_n = _safe_len("materials")
    textures_n  = _safe_len("textures")
    if not materials_n and not textures_n:
        warnings.append("nenhum material/textura — asset pode parecer básico")

    return {
        "valid": True,
        "file": str(path),
        "size_bytes": path.stat().st_size,
        "polycount": polycount,
        "meshes": len(meshes),
        "materials": materials_n,
        "textures": textures_n,
        "animations": _safe_len("animations"),
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
