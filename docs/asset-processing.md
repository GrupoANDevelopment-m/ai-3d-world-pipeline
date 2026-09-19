# 🧹 Processamento de Assets

> Padronização universal entre Caminho A e Caminho B, antes da montagem final.

Esta camada recebe **qualquer asset** (mesh do COLMAP, splat do LichtFeld, GLB do TerraForge, etc.) e devolve **um asset pronto para engine**.

---

## Pipeline de Processamento

```
[Asset bruto]
      │
      ▼
┌────────────────────────┐
│ 1. Limpeza de mesh     │  ← remove faces degeneradas, buracos, ruído
└────────────┬───────────┘
             ▼
┌────────────────────────┐
│ 2. Retopologia         │  ← reduz polycount mantendo silhouette
└────────────┬───────────┘
             ▼
┌────────────────────────┐
│ 3. Geração de LODs     │  ← 4 níveis (LOD0 → LOD3)
└────────────┬───────────┘
             ▼
┌────────────────────────┐
│ 4. Atlas de texturas   │  ← une texturas em atlas PBR
│    PBR                 │
└────────────┬───────────┘
             ▼
┌────────────────────────┐
│ 5. Collider            │  ← gera colliders simples (Box / Capsule /
│                        │    ConvexHull / Trimesh)
└────────────┬───────────┘
             ▼
┌────────────────────────┐
│ 6. Conversão / Validação│  ← GLB final + gltf-validator
└────────────────────────┘
```

---

## Implementação

`tools/python/asset_processor.py` orquestra tudo via Blender headless:

```bash
blender --background --python tools/python/asset_processor.py -- \
    --input ./input/factory_splat.ply \
    --output ./output/factory_splat.glb \
    --max-tris 200000 \
    --lod-levels 4 \
    --collider trimesh
```

---

## Parâmetros Recomendados

| Cenário | max_tris | lod_levels | collider |
|---------|----------|------------|----------|
| Hero asset (player, veículo) | 100k | 4 | ConvexHull |
| Prop grande (casa, árvore) | 30k | 3 | Box |
| Vegetação scatter | 500 | 2 | Capsule |
| Terreno | 500k | 2 | Trimesh |
| Splat (3DGS) | n/a (render direto) | n/a | n/a |

---

## Conversões Comuns

| De | Para | Comando |
|----|------|---------|
| `.ply` | `.glb` | `gltf-transform optimize input.ply output.glb` |
| `.fbx` | `.glb` | `blender --background --python fbx_to_glb.py` |
| `.obj` | `.glb` | `blender --background --python obj_to_glb.py` |
| `.splat` | `.ksplat` | `splat-to-ksplat input.splat output.ksplat` |
| `.spz` | `.splat` | `spz-to-splat input.spz output.splat` |

---

## Validação Pré-Export

Antes de marcar o asset como "pronto":

```python
import gltflib

def validate_gltf(path: str) -> dict:
    gltf = gltflib.GLTF.load(path)
    report = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "polycount": 0,
        "texture_count": 0,
    }

    for mesh in gltf.meshes:
        for prim in mesh.primitives:
            report["polycount"] += prim.indices.count // 3

    if report["polycount"] > MAX_POLYCOUNT:
        report["warnings"].append("polycount acima do recomendado")

    return report
```

Bloqueia o pipeline se `valid == False`.
