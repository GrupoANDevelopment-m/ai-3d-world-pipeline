# 📸 Caminho A — Reconstrução (dados reais)

> Para engenharia, digital twins, preservação, simulação física.

Ideal quando o input são **dados reais capturados do mundo físico**.

---

## Fluxo Completo

```
[Imagens / Vídeo / Drone]
        │
        ▼
┌─────────────────────────┐
│ 1. SfM (Structure-from- │
│    Motion)              │  ← COLMAP ou Meshroom
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 2. MVS / Dense          │
│    Reconstruction       │  ← COLMAP dense OU WebODM (drone)
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 3. 3D Gaussian Splat    │  ← LichtFeld Studio
│    (visualização)       │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 4. Extração de mesh     │  ← opcional, para física/colisão
│    (do splat)           │
└─────────────────────────┘
```

---

## Etapa 1 — Structure-from-Motion (SfM)

Recupera poses das câmeras e pontos esparsos 3D.

### COLMAP

```bash
# Automático: feature extraction + matching + sparse reconstruction
colmap automatic_reconstructor \
    --workspace_path ./colmap_workspace \
    --image_path ./input_photos/
```

**Saídas**: `cameras.txt`, `images.txt`, `points3D.txt`.

### Meshroom (AliceVision)

```bash
meshroom_batch \
    --input ./input_photos/ \
    --output ./meshroom_cache/ \
    --pipeline ./tools/pipelines/meshroom_photogrammetry.mg
```

**Quando usar**: projetos que precisam de presets visuais amigáveis.

---

## Etapa 2 — Dense Reconstruction

### COLMAP dense

```bash
colmap image_undistorter \
    --image_path ./input_photos/ \
    --input_path ./colmap_workspace/sparse/0 \
    --output_path ./colmap_workspace/dense

colmap patch_match_stereo \
    --workspace_path ./colmap_workspace/dense

colmap stereo_fusion \
    --workspace_path ./colmap_workspace/dense \
    --output_path ./colmap_workspace/dense/fused.ply
```

### WebODM (drone, georreferenciado)

```bash
docker run -ti --rm \
    -v $(pwd)/webodm_output:/datasets \
    opendronemap/odm \
    --project-path /datasets project_new
```

**Vantagem**: gera ortofoto + DEM + nuvem de pontos em **coordenadas reais (EPSG:4326 ou UTM)**.

API REST disponível em `http://localhost:8000/api/`.

---

## Etapa 3 — 3D Gaussian Splatting (LichtFeld Studio)

Estado da arte para visualização fotorrealista. Tempo real.

```bash
# Treinamento (LichtFeld)
lichtfeld train \
    --data ./input_photos \
    --output ./gaussian_splatting/scene.ply \
    --iterations 30000 \
    --sh-degree 3
```

**Saída**: `.ply` com Gaussianas (pode ser convertido para `.splat`/`.spz`/`.ksplat` para engines).

### Visualização

LichtFeld vem com viewer interativo. Para embed em engine:

- **Godot 4**: plugin `gsplat`.
- **Unity 6**: package `com.aras-p.gsplats`.
- **UE5**: plugin `UE5GaussianSplatting`.

---

## Etapa 4 — Extração de Mesh (opcional)

Para física, colisão, ray-cast:

```bash
# Marching Cubes sobre o splat (LichtFeld)
lichtfeld extract-mesh \
    --input ./gaussian_splatting/scene.ply \
    --output ./mesh/extracted.glb \
    --resolution 256
```

Ou usar a nuvem densa do COLMAP direto:

```bash
colmap poisson_mesher \
    --input_path ./colmap_workspace/dense/fused.ply \
    --output_path ./mesh/poisson.ply
```

---

## Métricas de Qualidade

| Métrica | Ferramenta | Alvo |
|---------|-----------|------|
| Reprodutibilidade SfM | COLMAP `mapper_evaluation` | ≥ 95% imagens registradas |
| Densidade de pontos | CloudCompare | ≥ 100 pts/cm² |
| Erro de reprojeção | COLMAP report | ≤ 1 px |
| Drift acumulado | OpenCV compare | ≤ 0.5% do trajeto |
| FPS visualização | godot/unity profiler | ≥ 60 fps |
| Georreferenciamento | WebODM GCP | ≤ 5 cm |

---

## Quando NÃO usar este caminho

- Você quer **criatividade total** sem referência real.
- Você precisa de **variação infinita** (ex: mundos de jogo roguelike).
- O custo de captura é proibitivo.

Nesses casos, vá para o [Caminho B](path-b-procedural.md).
