---
name: gaussian-splatting
version: 0.1.0
triggers:
  - "gaussian splatting"
  - "3dgs"
  - "splat fotorrealista"
  - "lichtfeld"
inputs:
  required:
    - photos_dir: string
  optional:
    - cameras_file: string  # resultado do photogrammetry
    - iterations: int       # default 30000
    - sh_degree: int        # default 3
outputs:
  type: splat
  format: ply | spz | ksplat | splat
calls:
  - tool: lichtfeld
    method: cli
fallbacks:
  - if: gpu_oom
    then: reduce_resolution
  - if: lichtfeld_unavailable
    then: original_3dgs_implementation
---

# ✨ Skill: Gaussian Splatting (3DGS)

Geração de cena fotorrealista em tempo real usando **3D Gaussian Splatting**.

---

## Quando o agente ativa

- Imediatamente após `photogrammetry`, para visualização.
- Quando o usuário pede "render realista em tempo real".
- Quando o output será exibido em engine com suporte a splat.

---

## Treinamento

```bash
lichtfeld train \
    --data ./input_photos/ \
    --cameras ./output/cameras.json \
    --output ./output/scene.ply \
    --iterations 30000 \
    --sh-degree 3 \
    --resolution 1920x1080
```

**Duração típica**: 10-30 min em RTX 3080+.

**Saída**: `.ply` com milhões de gaussianas (tamanho: 500 MB – 2 GB).

---

## Compressão / Otimização

Para uso em engine (tempo real), comprima:

```bash
# .ply → .ksplat (compressão proprietária)
splat-tool compress --input scene.ply --output scene.ksplat --quality high

# .ply → .spz (Niantic, melhor compressão)
spz-encode --input scene.ply --output scene.spz

# .ply → .splat (formato INRIA original)
splat-convert --input scene.ply --output scene.splat
```

| Formato | Tamanho relativo | Qualidade | Engine |
|---------|------------------|-----------|--------|
| `.ply` | 100% | perfeita | pesquisa |
| `.splat` | ~50% | alta | maioria |
| `.ksplat` | ~30% | alta | Godot (gsplat) |
| `.spz` | ~15% | muito alta | Unity, UE5 |

---

## Integração com Engines

### Godot 4

```bash
# Plugin: https://github.com/aras-p/UnityGaussianSplatting (port para Godot)
# ou https://github.com/lfranke/godot_gsplat
```

```gdscript
# Carregar no Godot
var splat_viewport = preload("res://addons/gsplat/viewport.tscn").instantiate()
splat_viewport.splat_file = "res://assets/splats/scene.spz"
add_child(splat_viewport)
```

### Unity 6

```bash
# Package: https://github.com/aras-p/UnityGaussianSplatting
```

### Unreal Engine 5

```bash
# Plugin: https://github.com/mkkellogg/GaussianSplats3D
```

---

## Parâmetros

| Parâmetro | Default | Efeito |
|-----------|---------|--------|
| `iterations` | 30000 | Mais iterações = melhor qualidade |
| `sh_degree` | 3 | View-dependent color (0-3) |
| `resolution` | 1920x1080 | Treinamento |
| `densify_grad_threshold` | 0.0002 | Quando criar gaussianas novas |
| `opacity_reset_interval` | 3000 | Reset de opacidade periódico |

---

## Limitação Conhecida

- Splats **não têm mesh** — não servem para colisão/física. Para isso, extraia mesh via `extract-mesh` ou use o Caminho A em paralelo.
- Treinamento requer GPU dedicada (mín. 8 GB VRAM).

---

## Saída para próxima Skill

```json
{
  "splat_file": "./output/scene.spz",
  "size_mb": 145,
  "iterations_used": 30000,
  "ssim": 0.94,
  "psnr": 28.3,
  "preview_image": "./output/preview.jpg"
}
```

Encaminha para `skills/scene-assembly.md`.
