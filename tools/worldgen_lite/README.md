# WorldGen-Lite — CPU-compatible 3D scene generation

## O que é

Implementação LEVE do [ZiYang-xie/WorldGen](https://github.com/ZiYang-xie/WorldGen)
que roda em hardware limitado. **Skipa partes GPU-only** mas mantém a pipeline geral.

## Pipeline original (ZiYang-xie/WorldGen)

```
text prompt ──[FLUX.1-dev]──▶ panoramic image ──[DA-2]──▶ depth
                                                            │
                                                            ├─[ml-sharp]──▶ Gaussian Splatting
                                                            └─────────────▶ Mesh
```

## Pipeline nossa (CPU-compatible)

```
text prompt ──[Stable Diffusion (skip se HF_TOKEN)]──▶ panoramic image
   OU
input panorama image ──────────────────────────────────┘
                                                          │
                                                          ├─[simple depth via gradient/SGM]──▶ depth
                                                          └─[load DA-2 se disponível]
                                                                                │
                                                                       open3d mesh from RGBD
                                                                                │
                                                                          salva .ply/.obj
                                                                                │
                                                                       exporta pra Godot
```

## Como usar

```bash
# Image → Mesh (skip text-to-image)
python3 -m tools.worldgen_lite.i2mesh --input panorama.jpg --output scene.ply

# Text → Mesh (requer Stable Diffusion local ou HF_TOKEN)
HF_TOKEN="if_have_key" python3 -m tools.worldgen_lite.t2mesh --prompt "cozy bedroom" --output scene.ply
```

## Componentes

1. **panorama_to_depth.py** — estima profundidade de panorama via gradients/luminance (CPU)
2. **depth_to_mesh.py** — converte RGBD panorama → 3D mesh via open3d (CPU)
3. **i2mesh.py** — image→mesh pipeline (combina acima)
4. **t2mesh.py** — text→image→mesh (text→image requer API/Stable Diffusion local)

## Limitações

- **Sem FLUX.1-dev** (gated, requer login + license acceptance)
- **Sem ml-sharp** (GPU-only Gaussian Splatting refiner)
- **Sem DA-2** (modelo grande + GPU-heavy para inferência CPU rápida)
- **Depth estimator simples** baseado em gradient + luminance (não tão preciso quanto DA-2)
- **Output**: mesh (.ply) ao invés de Gaussian Splatting

## Quando FLUX / DA-2 ficarem disponíveis:

Se você fornecer:
- `HF_TOKEN` (FLUX.1-dev gated)
- GPU disponível para DA-2

A pipeline pode ser melhorada adicionando:
- `pano_gen.py` (FLUX + Nunchaku)
- `pano_depth.py` (DA-2 real)

Nosso wrapper `worldgen_lite` já detecta essas deps e usa se disponíveis.
