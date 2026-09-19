# Exemplo: Digital Twin Híbrido

> Caso de uso: **fábrica real** (de fotos drone) + **terreno montanhoso procedural** ao redor.

---

## Cenário

A empresa quer um digital twin da sua fábrica:

- A **fábrica em si** deve ser **fotorrealista** (visitantes remotos em VR).
- O **terreno ao redor** (1 km²) é gerado proceduralmente — sem custo de captura extra.

## Input

```
input/
├── drone_factory/
│   ├── DJI_0001.jpg ... DJI_0120.jpg   (120 fotos drone, GPS)
│   └── gcps.txt                          (Ground Control Points, opcional)
└── reference_prompt.txt                  → "Terreno montanhoso, vegetação rasteira, estradas de terra"
```

## Comando

```bash
python tools/python/pipeline_runner.py \
    --pipeline pipelines/hybrid.yaml \
    --var photos_dir=./input/drone_factory/ \
    --var terrain_prompt="Terreno montanhoso, vegetação rasteira, estradas de terra" \
    --var output_dir=./outputs/factory_digital_twin/
```

## Diagrama do Fluxo Real

```
        ┌──────────────────────────┐
        │   120 fotos drone        │
        │   + bbox 1 km²           │
        └────────────┬─────────────┘
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
┌────────────────┐         ┌────────────────┐
│  Caminho A     │         │  Caminho B     │
│  COLMAP dense  │         │  TerraForge    │
│  → LichtFeld   │         │  (1 km²)       │
│  → .ksplat     │         │                │
└────────┬───────┘         └────────┬───────┘
         ▼                          ▼
   splat fotorrealista      mesh do terreno
   (~ 35 MB .ksplat)        (~ 500k tri)
         │                          │
         │      ┌──────────┐        │
         └─────►│  Godot 4 │◄───────┘
                │ (monta)  │
                └─────┬────┘
                      ▼
            ┌────────────────────┐
            │ outputs/scene.godot/│
            │ + vegetação        │
            │ + iluminação       │
            └────────────────────┘
```

## Saídas

```
outputs/factory_digital_twin/
├── factory/
│   ├── colmap/dense/fused.ply
│   └── splat/scene.ksplat         ← fotorrealista, pronto para VR
├── terrain/
│   ├── heightmap.png
│   └── terrain.glb
├── vegetation/                     ← casas, árvores, estradas
├── final/
│   ├── factory.glb                 ← com LODs e collider
│   └── terrain.glb
└── scene.godot/                    ← projeto Godot 4 completo
    ├── project.godot
    ├── scenes/main.tscn
    ├── assets/
    └── scripts/
```

## Uso no Godot

```bash
# Abrir o projeto
godot --editor outputs/factory_digital_twin/scene.godot/

# Ou rodar diretamente
godot --path outputs/factory_digital_twin/scene.godot/
```

## Tempo Estimado (RTX 3080 + Godot headless render)

| Etapa | Tempo |
|-------|-------|
| SfM + Dense MVS da fábrica | ~40 min |
| 3DGS treinamento | ~30 min |
| TerraForge terrain | ~2 min |
| GameFactory vegetation | ~5 min |
| Asset processing (Blender) | ~10 min |
| Assembly no Godot | ~3 min |
| Validação | ~2 min |
| **Total** | **~90 min** |

## Validação Final

```json
{
  "splat": {
    "ssim": 0.93,
    "psnr": 27.8,
    "size_mb": 38
  },
  "terrain": {
    "heightmap_resolution": "2048x2048",
    "mesh_polycount": 487_213,
    "biome": "mountain"
  },
  "scene": {
    "fps_godot": 72,
    "draw_calls": 1247,
    "vram_mb": 4096
  },
  "validation_passed": true
}
```
