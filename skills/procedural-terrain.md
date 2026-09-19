---
name: procedural-terrain
version: 0.1.0
triggers:
  - "terreno procedural"
  - "heightmap"
  - "terrain generation"
  - "geração de terreno"
inputs:
  required:
    - biome: coastal | desert | mountain | forest | tundra | volcanic | grassland
    - size_km: float
  optional:
    - seed: int
    - resolution: int  # default 2048
    - max_height_m: float
    - features:
        - erosion: bool
        - rivers: bool
        - caves: bool
outputs:
  type: heightmap | mesh
  format: png | raw | glb
calls:
  - tool: terraforge3d
    method: cli
  - tool: simplex_terrain
    method: godot_script
  - tool: terrain3d
    method: godot_native
fallbacks:
  - if: terraforge_unavailable
    then: simplex_terrain_in_godot
  - if: no_godot
    then: python_noise_lib
---

# ⛰️ Skill: Procedural Terrain

Gera terreno procedural de alta qualidade a partir de biomas.

---

## Quando o agente ativa

- Input contém `prompt` com menção a terreno, montanhas, paisagem.
- Intent declarada = `procedural` ou `hybrid`.
- Necessário heightmap + PBR textures + scattering.

---

## Opções

### A — TerraForge3D (multi-engine)

```bash
terraforge generate \
    --biome mountain \
    --size-km 4 \
    --resolution 2048 \
    --seed 42 \
    --features "erosion,rivers" \
    --output ./output/terrain.glb \
    --heightmap ./output/heightmap.png
```

### B — Godot 4 nativo (SimpleXTerrain + Terrain3D)

```gdscript
@tool
extends Node3D

func generate_mountain_terrain():
    var simplex = SimpleXTerrain.new()
    simplex.seed = 42
    simplex.size = Vector2(4096, 4096)
    simplex.height_range = Vector2(0, 800)
    
    # Multi-octave noise
    simplex.octaves = 6
    simplex.persistence = 0.5
    simplex.lacunarity = 2.0
    
    var heightmap = simplex.generate()
    
    var terrain = Terrain3D.new()
    terrain.region_size = 1024
    terrain.vertex_density = 256.0
    terrain.heightmap = heightmap
    
    # PBR por região de altura (biome blending)
    var mat = preload("res://materials/mountain_blend.tres")
    mat.set_splat_map(simplex.generate_biome_map(["rock", "grass", "snow"]))
    terrain.material = mat
    
    add_child(terrain)
```

### C — Python puro (fallback, sem Godot)

```python
from opensimplex import OpenSimplex
from PIL import Image
import numpy as np

def generate_heightmap(size=2048, seed=42, scale=128.0, octaves=6):
    gen = OpenSimplex(seed=seed)
    heightmap = np.zeros((size, size), dtype=np.float32)
    
    for y in range(size):
        for x in range(size):
            nx, ny = x / size - 0.5, y / size - 0.5
            amp, freq = 1.0, 1.0
            total = 0
            for o in range(octaves):
                total += gen.noise2(nx * freq * scale, ny * freq * scale) * amp
                amp *= 0.5
                freq *= 2.0
            heightmap[y, x] = (total + 1) / 2
    
    img = Image.fromarray((heightmap * 65535).astype(np.uint16), mode="I;16")
    img.save("./output/heightmap.png")
    return heightmap
```

---

## Biomas Suportados

| Bioma | height_range | features | densidade de vegetação |
|-------|--------------|----------|------------------------|
| coastal | 0–50 m | beaches, dunes | alta (palmeiras) |
| desert | 0–200 m | dunes, mesas | baixa |
| mountain | 0–3000 m | peaks, glaciers | média |
| forest | 0–300 m | hills, rivers | altíssima |
| tundra | 0–500 m | permafrost | muito baixa |
| volcanic | 0–4000 m | lava, craters | nenhuma |
| grassland | 0–200 m | plains | média |

---

## Erosion Simulation (opcional, mas recomendado)

```bash
# HEM (Hydraulic Erosion) — fluid simulation
terraforge erode \
    --heightmap ./output/heightmap.png \
    --iterations 100000 \
    --water-level 0.3 \
    --output ./output/heightmap_eroded.png
```

Sem erosão: terreno parece "plástico demais". Com erosão: realismo geológico.

---

## Splat Map (biome blending)

Para Terrain3D (Godot) ou Unity Terrain:

```python
# 4 camadas: rock / grass / sand / snow
splat_map = generate_splat_map(
    heightmap, layers=[
        ("rock",  lambda h: 1.0 if h > 0.7 else 0.0),
        ("grass", lambda h: smoothstep(0.3, 0.5, h) * (1 - smoothstep(0.7, 0.85, h))),
        ("sand",  lambda h: smoothstep(0.4, 0.55, h) * (1 - smoothstep(0.55, 0.7, h))),
        ("snow",  lambda h: smoothstep(0.85, 0.95, h)),
    ]
)
splat_map.save("./output/splat.png")
```

---

## Saída para próxima Skill

```json
{
  "heightmap": "./output/heightmap.png",
  "splat_map": "./output/splat.png",
  "mesh": "./output/terrain.glb",
  "bounds_m": [4000, 4000],
  "max_height_m": 800,
  "biome": "mountain"
}
```

Encaminha para `skills/scene-assembly.md` e opcionalmente `skills/worldgen.md` (para vegetação).
