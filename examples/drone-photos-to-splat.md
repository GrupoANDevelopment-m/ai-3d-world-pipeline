# Exemplo: Fotos de Drone → Gaussian Splat

> Caso de uso: **digital twin** de uma fábrica a partir de 120 fotos de drone.

---

## Input

- 120 fotos `.jpg` em `./input/drone_factory/`
- Drone com GPS (georreferenciamento opcional via WebODM)
- Resolução média: 5472×3648 px
- Sobreposição média: 75%

## Comando

```bash
python tools/python/pipeline_runner.py \
    --pipeline pipelines/reconstruction.yaml \
    --var photos_dir=./input/drone_factory/ \
    --var output_dir=./outputs/factory_splat/
```

## O que acontece

1. **SfM esparso** (COLMAP): registra ~118 das 120 fotos, gera ~52k pontos 3D.
2. **Dense MVS** (COLMAP patch_match_stereo): ~18M pontos densos.
3. **3DGS** (LichtFeld): treina 30k iterações, gera ~2M gaussianas.
4. **Compressão**: `.ply` → `.ksplat` (~120 MB → ~35 MB).
5. **Mesh extract**: para física/colisão, mesh decimada a 200k triângulos.

## Saídas

```
outputs/factory_splat/
├── colmap/
│   ├── sparse/0/{cameras,images,points3D}.bin
│   └── dense/fused.ply
├── splat/
│   ├── scene.ply
│   ├── scene.ksplat
│   └── meta.json
├── mesh/
│   └── extracted.glb
└── report.json
```

## Tempo estimado (RTX 3080)

| Etapa | Tempo |
|-------|-------|
| SfM esparso | ~10 min |
| Dense MVS | ~25 min |
| 3DGS treinamento | ~30 min |
| Mesh extract | ~5 min |
| **Total** | **~70 min** |

## Integração no Godot

```gdscript
# Carregar o splat no Godot 4
var splat_viewport = preload("res://addons/gsplat/viewport.tscn").instantiate()
splat_viewport.splat_file = "res://assets/factory.ksplat"
add_child(splat_viewport)

# Carregar o mesh para colisão
var factory_mesh = preload("res://scenes/factory_mesh.tscn").instantiate()
add_child(factory_mesh)
```

## Validação

```json
{
  "ssim": 0.94,
  "psnr": 28.3,
  "registered_images": 118,
  "reprojection_error_mean": 0.62,
  "splat_size_mb": 35,
  "fps_godot_preview": 72
}
```
