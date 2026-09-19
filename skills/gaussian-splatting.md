---
name: gaussian-splatting
version: 0.3.0
triggers:
  - "gaussian splatting"
  - "3dgs"
  - "splat fotorrealista"
  - "lichtfeld"
  - "supersplat"
  - "edit splat"
inputs:
  required:
    - photos_dir: string
    - mode: train | edit | optimize
  optional:
    - cameras_file: string
    - iterations: int
    - sh_degree: int
    - compress: ksplat | spz | splat | none
    - optimize_quality: high | medium | low
outputs:
  type: splat
  format: ply | spz | ksplat | splat
calls:
  - tool: lichtfeld
    method: cli
  - tool: supersplat
    method: web_ui_or_cli
  - tool: blender_process
    method: python
fallbacks:
  - if: lichtfeld_unavailable
    then: original_3dgs
  - if: gpu_oom
    then: reduce_resolution
  - if: compress_unavailable
    then: keep_ply
---

# ✨ Skill: Gaussian Splatting (3DGS) + Edição

Geração, edição e otimização de cenas Gaussian Splat.

---

## Modos

### A — Treinar (LichtFeld Studio)

> Repo: https://lichtfeld.io / https://github.com/RobertKrajewski/LichtFeld-Studio

```bash
bash tools/cli-wrappers/lichtfeld.sh \
    --photos ./drone_photos/ \
    --output ./scene/ \
    --iter 30000 \
    --sh 3 \
    --resolution 1920x1080 \
    --compress ksplat
```

**Saída**: `.ply` (treino) + `.ksplat` (comprimido para engine).

**Duração típica**: 10-30 min em RTX 3080+.

### B — Editar (SuperSplat — PlayCanvas)

> Repo: https://github.com/playcanvas/supersplat
> Web editor: https://superspl.at/editor

```bash
# Subir editor web localmente
bash tools/cli-wrappers/supersplat.sh serve --port 3000

# Otimização batch (delega ao lichtfeld)
bash tools/cli-wrappers/supersplat.sh optimize \
    --input scene.ply --output scene.spz --quality high
```

**Recursos do SuperSplat**:
- Inspeção visual
- Edição de splats (transform, delete, recolorir)
- Otimização (reduce count)
- Publicação direta

**Requisitos**: Node.js 20.19+

### C — Visualizar (Godot 4 / Unity 6 / UE5)

| Engine | Plugin/Asset |
|--------|--------------|
| Godot 4 | `godot_gsplat` ou `aras-p/UnityGaussianSplatting` port |
| Unity 6 | `aras-p/UnityGaussianSplatting` (package) |
| UE5 | `mkkellogg/GaussianSplats3D` (plugin) |

---

## Compressão / Otimização

| Formato | Tamanho | Qualidade | Engine |
|---------|---------|-----------|--------|
| `.ply` | 100% | perfeita | pesquisa |
| `.splat` | ~50% | alta | maioria |
| `.ksplat` | ~30% | alta | Godot (gsplat) |
| `.spz` | ~15% | muito alta | Unity, UE5 |

```bash
# LichtFeld gera direto .ksplat (configurável)
lichtfeld train ... --compress ksplat

# Conversões
splat-tool compress --input scene.ply --output scene.ksplat --quality high
spz-encode --input scene.ply --output scene.spz
splat-convert --input scene.ply --output scene.splat
```

---

## Parâmetros de Treino

| Parâmetro | Default | Efeito |
|-----------|---------|--------|
| `iterations` | 30000 | Mais = melhor |
| `sh_degree` | 3 | View-dependent color (0-3) |
| `resolution` | 1920x1080 | Treino |
| `densify_grad_threshold` | 0.0002 | Quando criar novas gaussianas |
| `opacity_reset_interval` | 3000 | Reset de opacidade periódico |

---

## Limitação

- Splats **não têm mesh** → não servem para colisão/física. Use o Caminho A em paralelo para extrair mesh.

---

## Workflow Típico (Híbrido)

```bash
# 1. Treina splat (visualização fotorrealista)
bash lichtfeld.sh --photos drone/ --output splat/ --compress ksplat

# 2. Extrai mesh do splat (física/colisão)
bash blender_process.sh --input splat/scene.ply --output mesh/extracted.glb \
    --max-tris 200000 --lod-levels 4 --collider trimesh

# 3. Edita splat (limpar ruído, melhorar densidade)
bash supersplat.sh serve

# 4. Carrega no engine
godot --headless --script load_splat.gd
```

---

## Saída

```json
{
  "splat_file": "./scene/scene.ksplat",
  "size_mb": 145,
  "iterations_used": 30000,
  "ssim": 0.94,
  "psnr": 28.3,
  "preview_image": "./scene/preview.jpg"
}
```
