---
name: photogrammetry
version: 0.1.0
triggers:
  - "fotogrametria"
  - "photogrammetry"
  - "reconstrução 3d"
  - "structure from motion"
  - "sfm"
inputs:
  required:
    - photos_dir: string
  optional:
    - mask_dir: string
    - camera_model: OPENCV | SIMPLE_PINHOLE
    - matching: exhaustive | sequential | vocab_tree
outputs:
  type: pointcloud | mesh
  format: ply | obj | glb
calls:
  - tool: colmap
    method: cli
  - tool: meshroom
    method: cli
  - tool: webodm
    method: docker
fallbacks:
  - if: colmap_fails
    then: meshroom
  - if: no_gpu
    then: colmap_cpu_only
---

# 📸 Skill: Photogrammetry

Recupera geometria 3D a partir de fotos / vídeo.

---

## Quando o agente ativa

- Input contém diretório com `.jpg`/`.jpeg`/`.png`/`.tif`.
- Input contém arquivo `.mp4`/`.mov` (extrai frames antes).
- Intent declarada = `reconstruction`.

---

## Pipeline Padrão

```
[photos_dir/]
     │
     ▼
[1] Frame extraction (se vídeo)
     │
     ▼
[2] SfM (COLMAP automatic_reconstructor)
     │
     ▼
[3] Dense MVS (COLMAP patch_match_stereo + stereo_fusion)
     │
     ▼
[4] Poisson meshing (opcional)
     │
     ▼
[output/sparse.ply | output/dense.ply | output/mesh.glb]
```

---

## Comando Padrão

```bash
# Wrapper
bash tools/cli-wrappers/colmap.sh \
    --photos ./input_photos/ \
    --output ./output/ \
    --type dense
```

Ou Python direto:

```python
from tools.python.colmap_runner import run_colmap_pipeline

result = run_colmap_pipeline(
    photos_dir="./input_photos/",
    output_dir="./output/",
    pipeline="dense",
    gpu=True,
    matching="exhaustive"  # para < 500 fotos
)
```

---

## Pré-requisitos

- **COLMAP 3.8+** instalado (`colmap --version`).
- GPU NVIDIA + CUDA (acelera 5-10x).
- Mínimo 30 fotos (ideal 100+) com overlap ≥ 60%.

---

## Drone / Georreferenciamento

Para drones com GPS, use **WebODM** no lugar do COLMAP direto:

```bash
docker run -ti --rm \
    -v $(pwd)/datasets:/datasets \
    opendronemap/odm \
    --project-path /datasets \
    --gcp-path /datasets/gcps.txt \
    project_new
```

Vantagens: ortofoto georreferenciada, DEM em EPSG:4326, nuvem de pontos em LAZ.

---

## Validação

| Métrica | Alvo |
|---------|------|
| Imagens registradas | ≥ 95% |
| Erro médio de reprojeção | ≤ 1 px |
| Pontos 3D esparsos | ≥ 10k |
| Pontos densos por cm² | ≥ 100 |

---

## Saída para próxima Skill

```json
{
  "sparse_pointcloud": "./output/sparse.ply",
  "dense_pointcloud": "./output/dense.ply",
  "mesh": "./output/mesh.glb",
  "cameras": "./output/cameras.json",
  "registered_images": 118,
  "reprojection_error_mean": 0.62
}
```

Encaminha para `skills/gaussian-splatting.md` ou diretamente para `skills/asset-processor.md`.
