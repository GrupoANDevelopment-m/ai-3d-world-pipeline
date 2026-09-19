---
name: classical-3dworld
version: 0.1.0
triggers:
  - "3dworld"
  - "engine opengl clássica"
  - "render fotorrealista legacy"
  - "universe generation"
inputs:
  required:
    - config: string  # arquivo .txt de config 3DWorld
  optional:
    - source: string
    - headless: string
    - timeout_s: int
outputs:
  type: scene | heightmap | mesh
  format: obj | mesh | modmap
calls:
  - tool: 3dworld
    method: cpp_binary
fallbacks:
  - if: 3dworld_unavailable
    then: use_alternative_engine
---

# 🌌 Skill: Classical 3DWorld (OpenGL)

Engine OpenGL clássica com geração procedural de terrenos, cidades, interiores, galáxias.

> Repo: https://github.com/fegennari/3DWorld

---

## Quando o agente ativa

- Render OpenGL clássico (legacy 4.5+).
- Geração de **universos inteiros** (estrelas, planetas, luas).
- Interiores de prédios com navegação.
- Cenários específicos: San Miguel, ice caves, museu, sponza.

---

## Capacidades

| Categoria | Features |
|-----------|----------|
| **Terreno** | Heightmap read/write, domain warp noise, hydraulic erosion |
| **Vegetação** | Árvores, grama, pedras |
| **Cidades** | Prédios com interiores/exteriores, estradas, decoração |
| **Universos** | Galáxias, estrelas, planetas, luas |
| **Voxels** | Sim |
| **Formatos entrada** | JPEG, PNG, BMP, TIFF, TGA, DDS, LW Object, 3DS, Assimp |
| **Formatos internos** | `.mesh`, `.modmap` |

---

## Configs de Exemplo (do repo)

| Arquivo | Cenário |
|---------|---------|
| `config_heightmap.txt` | Terreno a partir de heightmap |
| `config_t.txt` | Terreno simples |
| `config_white_plane.txt` | Plano branco (debug) |
| `universe/config_universe.txt` | Universo com galáxias |
| `sponza/config_sponza2.txt` | Sponza (modelo clássico) |
| `mapx/config_mapx.txt` | Mapa customizado |
| `config_museum.txt` / `config_san_miguel.txt` | Prédios com interiores |
| `config_ice_caves.txt` | Cavernas de gelo |
| `house/config_house.txt` | Casa explorável |
| `config_buildings_walkthrough.txt` | Walkthrough em prédios |

---

## Uso

```bash
bash tools/cli-wrappers/3dworld.sh \
    --config /path/to/3DWorld/configs/san_miguel.txt \
    --output ./san_miguel_capture \
    --timeout 600
```

**Variáveis de ambiente**:
- `THREEDWORLD_DIR` — caminho do repo
- `THREEDWORLD_HEADLESS` — wrapper headless (default: `xvfb-run -a`)
- `THREEDWORLD_TIMEOUT` — tempo de captura em segundos (default: 300)

**Build** (Linux):
```bash
make -f makefile -j$(nproc)
```

**Build** (Windows):
- Visual Studio 2019/2022
- Abrir `3DWorld.sln`, build x64

---

## Dependências

OpenGL 4.5, freeglut, glew, glm, OpenAL (opcional), libpng, libtiff, zlib, Assimp (opcional), libtarga, STB headers.

---

## Quando NÃO usar

- Quer compatibilidade moderna → use Godot 4 ou Unity.
- Quer text-to-3D → use WorldGen.
- Quer mobile → use Bycob/world.

Use 3DWorld quando quiser **fotorrealismo clássico** com OpenGL (boa para pesquisa, visualização, sim).
