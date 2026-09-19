---
name: procedural-terrain
version: 0.3.0
triggers:
  - "terreno procedural"
  - "heightmap"
  - "terrain generation"
  - "geração de terreno"
  - "godote terrain"
inputs:
  required:
    - biome: coastal | desert | mountain | forest | tundra | volcanic | grassland
    - size_km: float
    - engine: terraforge | terrain3d | simplex | python
  optional:
    - seed: int
    - resolution: int
    - max_height_m: float
    - features: [erosion, rivers, caves, biome_blend]
    - godot_project: string  # obrigatório se engine=terrain3d|simplex
outputs:
  type: heightmap | mesh
  format: png | raw | glb
calls:
  - tool: terraforge
    method: cli
  - tool: terrain3d
    method: godot_script
  - tool: bycob_world
    method: cpp
fallbacks:
  - if: terraforge_unavailable
    then: terrain3d_or_simplex
  - if: godot_unavailable
    then: python_noise_lib
  - if: no_gpu
    then: bycob_world_cpu
---

# ⛰️ Skill: Procedural Terrain

Gera terreno procedural de alta qualidade. Suporta 3 engines:

| Engine | Quando usar | Saída |
|--------|-------------|-------|
| **TerraForge3D** | Multi-engine, GPU, alta fidelidade, export .glb/.obj/.png | mesh + heightmap + splatmap |
| **Terrain3D + SimpleXTerrain** | Godot 4 nativo, runtime streaming | mesh do Godot + heightmap PNG |
| **Bycob/world** | Mundo massivo ilimitado, LOD automático | mesh C++ |
| **Python (OpenSimplex)** | Fallback sem GPU/engine | heightmap PNG |

---

## 1. TerraForge3D (Jaysmito101/TerraForge3D)

> https://github.com/Jaysmito101/TerraForge3D

Engine GPU com node editor. Gera + erosiona + texturiza em uma única passada.

```bash
# Wrapper
bash tools/cli-wrappers/terraforge.sh \
    --biome mountain \
    --size-km 4 \
    --resolution 2048 \
    --seed 42 \
    --erosion hydraulic \
    --output ./terrain \
    --format glb
```

**Saídas**: `terrain.glb`, `heightmap.png`, `splatmap.png`.

### Recursos do TerraForge3D
- 40+ nodes (math, noise, modifiers)
- Hydraulic + wind erosion
- Sea level ajustável
- Texture baking PBR (tiled ou full)
- Export: OBJ, GLTF, GLB, STL, PNG, JPG
- GLSL shader export

---

## 2. Terrain3D + SimpleXTerrain (Godot 4 nativo)

> Terrain3D: https://github.com/TokisanGames/Terrain3D
> SimpleXTerrain: https://github.com/prajwal-mx/SimpleXTerrain

```bash
bash tools/cli-wrappers/terrain3d.sh \
    --project ./mygame/ \
    --biome mountain \
    --size-km 4 \
    --resolution 2048 \
    --seed 42 \
    --output ./terrain
```

**Requisitos**:
- Godot 4.6+ (Mono)
- .NET SDK 8.0+

**Capacidades Terrain3D**:
- Até 65.5×65.5 km (4.295 km²) com regiões não contíguas
- Até 32 texturas PBR
- 10 LODs no mesh
- Foliage instancing + shadow impostor

**Capacidades SimpleXTerrain** (TerrainGraphResource):
- Perlin, Fractal, Voronoi, Radial, Splines, Heightmap images
- Levels, Curves, Slope masks
- Hydraulic + Thermal erosion
- Terraces, Beaches, Ledges, Blur
- Splatmaps + Biome blending

---

## 3. Bycob/world (C++ massivo)

> https://github.com/Bycob/world

```bash
bash tools/cli-wrappers/bycob_world.sh \
    --output ./world \
    --terrain \
    --vegetation \
    --cities \
    --voxels \
    --seed 42
```

**Recursos**:
- Terrenos, vegetação (árvores/grama/rochas), cidades
- LOD automático
- Exploração ilimitada em tempo real
- Opcional: Vulkan renderer (VkWorld), Irrlicht viewer (World3D)

---

## 4. Fallback Python (OpenSimplex)

Se nenhuma engine estiver disponível:

```python
from opensimplex import OpenSimplex
from PIL import Image
import numpy as np

def generate_heightmap(size=2048, seed=42, scale=128.0, octaves=6):
    gen = OpenSimplex(seed=seed)
    heightmap = np.zeros((size, size), dtype=np.float32)
    for y in range(size):
        for x in range(size):
            nx, ny = x/size - 0.5, y/size - 0.5
            amp, freq, total = 1.0, 1.0, 0.0
            for o in range(octaves):
                total += gen.noise2(nx*freq*scale, ny*freq*scale) * amp
                amp *= 0.5
                freq *= 2.0
            heightmap[y, x] = (total + 1) / 2

    img = Image.fromarray((heightmap * 65535).astype(np.uint16), mode="I;16")
    img.save("./heightmap.png")
    return heightmap
```

---

## Biomas Suportados

| Bioma | height_range | features |
|-------|--------------|----------|
| coastal | 0–50 m | beaches, dunes |
| desert | 0–200 m | dunes, mesas |
| mountain | 0–3000 m | peaks, glaciers |
| forest | 0–300 m | hills, rivers |
| tundra | 0–500 m | permafrost |
| volcanic | 0–4000 m | lava, craters |
| grassland | 0–200 m | plains |

---

## Erosion (opcional mas recomendado)

```bash
# Hydraulic erosion via TerraForge3D
bash terraforge.sh --biome mountain --erosion hydraulic --output ./mt

# Thermal + Hydraulic via SimpleXTerrain (no TerrainGraphResource)
# Configure nodes na GUI do Godot ou via script
```

Sem erosão: terreno parece "plástico demais". Com erosão: realismo geológico.

---

## Saída para próxima Skill

```json
{
  "engine": "terraforge3d",
  "heightmap": "./terrain/heightmap.png",
  "splat_map": "./terrain/splatmap.png",
  "mesh": "./terrain/terrain.glb",
  "bounds_m": [4000, 4000],
  "max_height_m": 800,
  "biome": "mountain"
}
```

Encaminha para `skills/scene-assembly.md` e opcionalmente `skills/worldgen.md` (vegetação).
