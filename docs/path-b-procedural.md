# 🌍 Caminho B — Geração Procedural + AI

> Para jogos, mundos criativos, prototipagem rápida, cenários fictícios.

Ideal quando o input é **criativo** (prompt / imagem de referência) e não há dados reais do mundo físico a reconstruir.

---

## Fluxo Completo

```
[Prompt / Imagem / OSM]
        │
        ▼
┌─────────────────────────┐
│ 1. WorldGen             │
│    (cena base)          │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 2. Terreno procedural   │
│    (heightmap + PBR)    │  ← TerraForge3D ou Terrain3D/SimpleXTerrain
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 3. Objetos / Props      │
│    (espalhamento AI)    │  ← GameFactory-3A
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 4. Geografia real       │
│    (OSM) [opcional]     │  ← rsgeotools
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 5. Vegetação / Cidades  │
│    (avançado)           │  ← 3DWorld ou Bycob/world
└─────────────────────────┘
```

---

## Etapa 1 — WorldGen (text-to-3D)

Gera uma cena 3D coerente a partir de prompt.

```python
from worldgen import SceneGenerator

generator = SceneGenerator(model="worldgen-xl")
scene = generator.generate(
    prompt="Vila costeira portuguesa com falésias e farol",
    style="realistic",
    reference_image="./refs/coastal.jpg",  # opcional
    resolution=(1920, 1080)
)
scene.export("./outputs/coastal/scene.glb")
```

**Saída**: cena base com skybox, terreno esquelético, lighting.

---

## Etapa 2 — Terreno Procedural

### Opção A — TerraForge3D (multi-engine)

```bash
terraforge generate \
    --biome coastal \
    --size_km 4 \
    --resolution 2048 \
    --seed 42 \
    --output ./outputs/coastal/terrain.glb \
    --heightmap ./outputs/coastal/heightmap.png
```

**Saídas**: mesh do terreno + heightmap PNG (16-bit).

### Opção B — Terrain3D + SimpleXTerrain (Godot 4 nativo)

```gdscript
# Godot 4 — script de geração
@tool
extends Node3D

func generate_terrain():
    var simplex = SimpleXTerrain.new()
    simplex.set_seed(42)
    simplex.set_size(Vector2(4096, 4096))
    simplex.set_height_range(0.0, 256.0)
    
    var terrain = Terrain3D.new()
    terrain.heightmap = simplex.generate_heightmap()
    terrain.material = preload("res://materials/grass_coastal.tres")
    add_child(terrain)
```

---

## Etapa 3 — Objetos e Props (GameFactory-3A)

O GameFactory-3A expõe operadores tipados:

```python
from gamefactory import GameFactory

gf = GameFactory()

# Objetos individuais
tree = gf.gen_3d_object(
    type="tree",
    style="mediterranean_oak",
    seed=7,
    output="./outputs/coastal/trees/oak_001.glb"
)

# Cena inteira com scatter
scene = gf.gen_3d_scene(
    prompt="Floresta de pinheiros costeiros com clareira",
    density="medium",
    biome="mediterranean",
    bounds=Box3(min=Vector3(0,0,0), max=Vector3(500,0,500)),
    output="./outputs/coastal/forest/"
)
```

**Saídas**: GLBs individuais + cena montada com scattering.

---

## Etapa 4 — Geografia Real (OSM) — opcional

Use quando quiser que **ruas, prédios e topografia** correspondam a um lugar real.

```python
from rsgeotools import OSMExtractor

osm = OSMExtractor(bbox=(38.7, -9.1, 38.8, -9.0))  # Lisboa
osm.fetch()
osm.export(
    buildings="./outputs/lisbon/buildings.glb",
    roads="./outputs/lisbon/roads.glb",
    vegetation="./outputs/lisbon/trees.glb"
)
```

Combinar com terreno da etapa 2 → digital twin leve.

---

## Etapa 5 — Vegetação / Cidades Avançadas

### 3DWorld (C++)

```bash
# Compilar (uma vez)
git clone https://github.com/mmlab/3DWorld.git
cd 3DWorld && cmake . && make

# Gerar
./3DWorld --build_scene --query "dense urban neighborhood" \
    --output ./outputs/urban/scene.bin
```

### Bycob/world

```python
import bycob_world as bw

world = bw.World()
world.generate_city(
    blocks=20,
    population=50000,
    style="european_modern",
    output="./outputs/city/"
)
```

---

## Pipeline YAML Declarativo

Exemplo (`pipelines/procedural.yaml`):

```yaml
name: coastal_village
version: 1.0.0

inputs:
  prompt: "Vila costeira portuguesa com falésias e farol"
  reference_image: ./refs/coastal.jpg
  osm_bbox: null  # não usar OSM

stages:
  - id: scene_base
    tool: worldgen
    params:
      style: realistic
      resolution: [1920, 1080]

  - id: terrain
    tool: terraforge
    params:
      biome: coastal
      size_km: 4
      resolution: 2048

  - id: vegetation
    tool: gamefactory
    params:
      scene: forest
      density: medium
      biome: mediterranean

  - id: assembly
    tool: godot
    params:
      engine_version: 4.3
      target_fps: 60
      lod_bias: 1.0

outputs:
  - ./outputs/coastal/scene.godot/
  - ./outputs/coastal/report.json
```

---

## Quando NÃO usar este caminho

- Você precisa de **fidelidade ao real** (ex: digital twin de fábrica).
- Existe dado de captura disponível.

Nesses casos, vá para o [Caminho A](path-a-reconstruction.md) ou combine os dois no [Caminho Híbrido](scene-assembly.md).
