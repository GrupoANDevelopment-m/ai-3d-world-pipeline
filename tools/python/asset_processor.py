#!/usr/bin/env python3
"""
asset_processor.py — Asset processing headless via Blender.

Operações:
  1. Importa mesh (.glb/.fbx/.obj/.ply)
  2. Retopologia (decimação se polycount > max_tris)
  3. Geração de LODs (4 níveis por padrão)
  4. Material PBR + atlas de texturas
  5. Colliders (Box / Convex Hull / Trimesh / Capsule)
  6. Exporta como .glb

Uso (CLI Blender):
    blender --background --python tools/python/asset_processor.py -- \\
        --input ./in.glb --output ./out.glb \\
        --max-tris 200000 --lod-levels 4 --collider trimesh

Uso (standalone Python para inspeção):
    python tools/python/asset_processor.py --validate-only --input ./out.glb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Quando rodando dentro do Blender, bpy está disponível.
# Quando rodando standalone, podemos apenas validar com gltflib.
try:
    import bpy  # type: ignore
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False


# =============================================================================
#  Bloco 1 — Processamento dentro do Blender
# =============================================================================

def process_in_blender(args: argparse.Namespace) -> None:
    """Roda todo o pipeline de processamento dentro do Blender."""
    import bpy  # noqa: F401

    print(f"[asset_processor] Importando {args.input}")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    ext = Path(args.input).suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(args.input))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(args.input))
    elif ext == ".obj":
        bpy.ops.import_scene.obj(filepath=str(args.input))
    elif ext == ".ply":
        # PLY precisa de addon 'io_mesh_ply'
        try:
            bpy.ops.wm.ply_import(filepath=str(args.input))
        except AttributeError:
            print("[asset_processor] PLY import requer addon 'io_mesh_ply'.")
            sys.exit(2)
    else:
        print(f"[asset_processor] Formato não suportado: {ext}")
        sys.exit(1)

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        print("[asset_processor] Nenhuma mesh encontrada no input.")
        sys.exit(2)

    print(f"[asset_processor] {len(meshes)} mesh(s) importada(s)")

    for obj in meshes:
        # 1. Decimação se necessário
        current_tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        if current_tris > args.max_tris:
            ratio = args.max_tris / current_tris
            print(f"[asset_processor] Decimando {obj.name}: "
                  f"{current_tris} → ~{args.max_tris} triângulos (ratio={ratio:.3f})")
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.modifier_add(type="DECIMATE")
            mod = obj.modifiers[-1]
            mod.ratio = ratio
            bpy.ops.object.modifier_apply(modifier=mod.name)

        # 2. Geração de LODs (mock — em produção usaríamos decimate progressivo)
        if args.lod_levels > 1:
            print(f"[asset_processor] Gerando {args.lod_levels} LODs")
            for i in range(1, args.lod_levels):
                lod_ratio = (args.lod_levels - i) / args.lod_levels
                lod_obj = obj.copy()
                lod_obj.data = obj.data.copy()
                lod_obj.name = f"{obj.name}_LOD{i}"
                bpy.context.collection.objects.link(lod_obj)
                # decimação LOD
                bpy.context.view_layer.objects.active = lod_obj
                lod_obj.select_set(True)
                bpy.ops.object.modifier_add(type="DECIMATE")
                mod = lod_obj.modifiers[-1]
                mod.ratio = max(0.05, lod_ratio)
                bpy.ops.object.modifier_apply(modifier=mod.name)

        # 3. Material PBR (placeholder — em produção aplicar atlas)
        if not obj.data.materials:
            mat = bpy.data.materials.new(name=f"{obj.name}_pbr")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Roughness"].default_value = 0.6
                bsdf.inputs["Metallic"].default_value = 0.0
            obj.data.materials.append(mat)

        # 4. Collider (metadata-only; em engine real gera-se mesh de colisão)
        obj["collider_type"] = args.collider
        obj["max_tris"] = args.max_tris
        obj["lod_levels"] = args.lod_levels

    # 5. Export GLB
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"[asset_processor] Exportando {output}")
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_materials="EXPORT",
        export_lights=False,
        export_cameras=False,
        export_yup=True,
        export_apply=True,
    )

    # 6. Meta
    meta_path = output.parent / f"{output.stem}.meta.json"
    meta = {
        "tool": "asset_processor",
        "input": str(args.input),
        "output": str(output),
        "max_tris_target": args.max_tris,
        "lod_levels": args.lod_levels,
        "collider": args.collider,
        "source_polycount": int(sum(
            len(p.vertices) - 2
            for obj in meshes for p in obj.data.polygons
        )),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"[asset_processor] Meta salvo em {meta_path}")
    print(f"[asset_processor] ✓ Concluído")


# =============================================================================
#  Bloco 2 — Validação standalone (sem Blender)
# =============================================================================

def validate_standalone(path: Path) -> None:
    """Valida um GLB já gerado, sem precisar de Blender."""
    try:
        import gltflib
    except ImportError:
        print("[asset_processor] instale gltflib para validar: pip install gltflib")
        sys.exit(2)

    print(f"[asset_processor] Validando {path}")
    gltf = gltflib.GLTF.load(str(path))
    polycount = 0
    for mesh in gltf.meshes:
        for prim in mesh.primitives:
            if prim.indices:
                polycount += prim.indices.count // 3

    report = {
        "file": str(path),
        "valid": True,
        "polycount": polycount,
        "meshes": len(gltf.meshes),
        "materials": len(gltf.materials),
        "textures": len(gltf.textures),
        "nodes": len(gltf.nodes),
    }
    print(json.dumps(report, indent=2))


# =============================================================================
#  Bloco 3 — Entry point
# =============================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Asset processor (Blender headless).")
    p.add_argument("--input", help="Mesh de entrada")
    p.add_argument("--output", help="Mesh de saída (.glb)")
    p.add_argument("--max-tris", type=int, default=200_000)
    p.add_argument("--lod-levels", type=int, default=4)
    p.add_argument("--collider",
                   choices=["trimesh", "convex", "box", "capsule"],
                   default="trimesh")
    p.add_argument("--validate-only", action="store_true",
                   help="Só valida um .glb existente (não precisa de Blender).")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.validate_only:
        if not args.input:
            print("Erro: --input obrigatório com --validate-only")
            return 1
        validate_standalone(Path(args.input))
        return 0

    if not args.input or not args.output:
        print("Erro: --input e --output obrigatórios.")
        return 1

    if not IN_BLENDER:
        print("[asset_processor] Este modo requer Blender. Use:")
        print("    blender --background --python tools/python/asset_processor.py -- \\")
        print("        --input in.glb --output out.glb")
        return 2

    process_in_blender(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
