---
name: worldgen-lite
version: 0.1.0
triggers:
  - "worldgen"
  - "text to scene"
  - "text to mesh"
  - "panorama to 3d"
  - "cena 3d de texto"
  - "gerar cena"
description: Adaptado do ZiYang-xie/WorldGen — gera cenas 3D a partir de texto ou panorama. CPU-only.
---

# 🌏 Skill: WorldGen-Lite

Adapta [ZiYang-xie/WorldGen](https://github.com/ZiYang-xie/WorldGen) pra rodar
em hardware limitado (CPU-only, sem GPU).

## Pipeline original (ZiYang-xie/WorldGen)

```
text prompt → [FLUX.1-dev] → panoramic image → [DA-2] → depth
                                                          ↓
                                                [ml-sharp] → Gaussian Splatting
                                                ou Poisson → mesh
```

## Nossa adaptação (CPU-only)

```
text prompt → panorama image (FLUX.1-dev real OR procedural fallback)
            ↓
            depth (heurística CPU OR DA-2 se disponível)
            ↓
            Poisson reconstruction → mesh (.ply/.obj)
            ↓
            export Godot
```

## Componentes disponíveis

| Tool | Função |
|------|--------|
| `worldgen_lite_i2mesh` | panorama → mesh (CPU) |
| `worldgen_lite_t2mesh` | text → mesh (FLUX gated OU procedural fallback) |

## Como usar (sem FLUX)

```bash
python3 -m tools.worldgen_lite.t2mesh \
    --prompt "snow mountain landscape" \
    --output scene.ply \
    --fallback-procedural
```

## Como usar (COM FLUX real)

1. Aceitar licença: https://huggingface.co/black-forest-labs/FLUX.1-dev
2. Login: `huggingface-cli login`
3. Rodar: `python3 -m tools.worldgen_lite.t2mesh --prompt "..." --hf-token $HF_TOKEN`

## Limitações conhecidas

- **Sem FLUX.1-dev**: usa panorama procedural baseada em keywords
  (sky/mountain/desert/forest/city/ocean/sunset)
- **Sem DA-2 real**: usa heurística de luminância + saturação + vertical position
- **Sem ml-sharp**: gera mesh ao invés de Gaussian Splatting
- **GPU-bound models skipped**: FLUX.1-dev, Nunchaku, ml-sharp, DA-2 (full)

## Quando GPU/HF_TOKEN disponível

Adicionar:
- `pano_gen.py` (FLUX + Nunchaku quantized)
- `pano_depth.py` (DA-2 real, melhor depth)
- `pano_sharp.py` (ml-sharp, melhor Gaussian Splatting)

Output esperado com GPU:
- 1024x1024 panorama via FLUX
- depth map precisa via DA-2
- Gaussian Splatting real-time renderable

## Substitutos já integrados

| Original | Substituto CPU |
|----------|----------------|
| FLUX.1-dev | procedural skybox + keywords |
| DA-2 | luminance/vertical heuristic |
| ml-sharp | Poisson reconstruction |
| Nunchaku | (n/a, era só FLUX quantizer) |