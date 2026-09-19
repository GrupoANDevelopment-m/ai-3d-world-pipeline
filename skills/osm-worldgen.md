---
name: osm-worldgen
version: 0.1.0
triggers:
  - "openstreetmap"
  - "osm to 3d"
  - "mundo real"
  - "cidade real"
  - "fusão com osm"
inputs:
  required:
    - tile_x: int
    - tile_y: int
  optional:
    - tiles_w: int
    - tiles_h: int
    - cache_dir: string
    - data_dir: string
    - output_dir: string
    - flat_terrain: bool
    - z_up: bool
    - merge: bool
    - format: ply | obj
outputs:
  type: mesh_layers
  format: ply | obj
calls:
  - tool: rsgeotools
    method: cli
fallbacks:
  - if: rsgeotools_unavailable
    then: manual_osm_to_obj
---

# 🗺️ Skill: OSM WorldGen

Gera **cidades e geografia reais** a partir do OpenStreetMap usando rsgeotools/rvtgen3d.

> Repo: https://github.com/romanshuvalov/rsgeotools

---

## Quando o agente ativa

- Input contém `osm_bbox` ou coordenadas de tile.
- Usuário quer uma cidade real (ex: "recrie o centro de Lisboa").
- Necessário complemento geográfico a um terreno procedural.

---

## Pipeline

```
[Bbox / tile coords (OSM zoom 14)]
        │
        ▼
[rsgeotools-rvtgen3d]
        │
        ├── Camada 0: surface (terreno + relevo)
        ├── Camada 1: buildings (prédios com telhados e decorações)
        ├── Camada 2: surface_map (area)
        ├── Camada 3: roads / rivers
        ├── Camada 4: naturals (parques, água)
        ├── Camada 5: props (árvores, mobiliário urbano)
        ├── Camada 6: wires (linhas elétricas, postes)
        ├── Camada 7: stripes (faixas de estrada)
        └── Camada 8: walls (muros, cercas)
        │
        ▼
[Output .ply com 9 camadas + vertex attributes]
```

---

## Uso

### 1. Preparar cache (uma vez, demora)

O cache do OSM planet é enorme. Etapas:

```bash
# Variáveis de ambiente
export RVT_O5M_DIR=/data/o5m
export RVT_SHP_DIR=/data/shp
export RVT_GPAK_DIR=/data/gpak
export RVT_CSV_CONF=/path/to/osm-conf.ini
export RVT_HGT_DIR_NASADEM=/data/nasadem
export RVT_HGT_DIR_ASTERGDEMV3=/data/aster

# 1. Inicializar planet OSM
RVT_O5M_DIR=$RVT_O5M_DIR rsgeotools-planet-init.sh planet-260101.osm.pbf

# 2. Processar ocean (water polygons)
cd $RVT_SHP_DIR
for i in 0 1 2 3 4 5 6 7; do
    rsgeotools-subdiv-shapefile.sh 0 0 0 $i ocean
done

# 3. Processar geodata (2-3 semanas para planet inteiro!)
rsgeotools-planet-process-full.sh 260101 0

# 4. Processar heightmap
rsgeotools-process-hm-full.sh
```

### 2. Gerar um tile

```bash
bash tools/cli-wrappers/rsgeotools.sh \
    --x 8580 --y 5611 \
    --w 2 --h 2 \
    --cache-dir /data/gpak \
    --output-dir ./lisbon \
    --obj \
    --z-up
```

### 3. Conversão para tile do OpenStreetMap

Para descobrir `tile_x, tile_y` em zoom 14 a partir de coordenadas geográficas:

```python
import math
def deg2tile(lat_deg, lon_deg, zoom=14):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = (lon_deg + 180.0) / 360.0 * n
    ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return int(xtile), int(ytile)

# Lisboa centro
x, y = deg2tile(38.7223, -9.1393)
print(x, y)  # ex: 8580, 5611
```

---

## Vertex Attributes Importantes

- **FlagsA** (cor alpha): tipo de textura — residential (1), commercial (2), industrial (4)
- **FlagsB** (normal.w): surface flags — roof (1), flat wall (4)
- **Surface Map RGB**: water (0,1,0), asphalt (0.2,0,0), grass (0.7,0,0), sand (0,0,0.2), rock (0,0,0.7)

---

## Combinação com Terreno Procedural

```bash
# 1. Gera terreno procedural da região (TerraForge3D)
bash terraforge.sh --biome coastal --size-km 4 --output ./terrain

# 2. Sobrepõe prédios reais do OSM
bash rsgeotools.sh --x 8580 --y 5611 --w 4 --h 4 \
    --cache-dir /data/gpak --output-dir ./city

# 3. Blender monta tudo em uma cena única
bash blender_process.sh \
    --input ./city/buildings.ply \
    --output ./final_city.glb \
    --max-tris 500000 \
    --lod-levels 3
```

---

## Saída

```json
{
  "tile_x": 8580, "tile_y": 5611,
  "tiles_w": 2, "tiles_h": 2,
  "format": "obj",
  "layers": ["surface", "buildings", "surface_map", "roads_rivers",
             "naturals", "props", "wires", "stripes", "walls"],
  "artifacts": {
    "city": "./lisbon/city.obj",
    "metadata": "./lisbon/meta.json"
  }
}
```
