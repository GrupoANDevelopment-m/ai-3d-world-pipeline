# AI 3D World Pipeline 🌍🤖

> Pipeline orquestrado por IA para geração e reconstrução de mundos 3D — unificando fotogrametria, Gaussian Splatting, geração procedural, mundos OSM e mundos voxel. Engine alvo preferencial: **Godot 4**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Engine: Godot 4](https://img.shields.io/badge/Engine-Godot%204-478CBF?logo=godot-engine)](https://godotengine.org/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org/)
[![Open Source](https://img.shields.io/badge/100%25-Open%20Source-brightgreen)]()

---

## 🎯 O que é

Um **pipeline modular e extensível** que permite a um **Coding Agent / Multi-Agent** (Claude Code, Codex, GameFactory-3A, ou agente customizado em LangGraph / CrewAI) decidir automaticamente entre **6 caminhos**:

- **A — Reconstrução** — fotos / drone → mesh + Gaussian Splat fotorrealista
- **B — Procedural + AI** — prompt / imagem → mundo 3D completo
- **C — OSM Real** — coordenadas reais → cidade 3D com prédios e ruas
- **D — Voxel / Infinito** — mundo estilo Minecraft massivo
- **E — Clássico OpenGL** — render fotorrealista legacy (3DWorld)
- **HYBRID** — combinação de A + B (digital twin completo)

O resultado é montado, validado e exportado para a engine alvo. Tudo **100% open source**.

---

## 🛠️ Ferramentas Integradas (15)

### Reconstrução (Caminho A)
| Ferramenta | Função | Wrapper | Repo |
|------------|--------|---------|------|
| **COLMAP** | Structure-from-Motion + Dense MVS | `colmap.sh` ✅ | [colmap/colmap](https://github.com/colmap/colmap) |
| **AliceVision** | Pipeline alternativo de fotogrametria | `alicevision.sh` ✅ | [alicevision/AliceVision](https://github.com/alicevision/AliceVision) |
| **Meshroom** | GUI node-based de fotogrametria | `meshroom.sh` ✅ | [alicevision/Meshroom](https://github.com/alicevision/Meshroom) |
| **WebODM** | Ortofotos, DEM, nuvem georreferenciada (drone) | `webodm.sh` ✅ | [OpenDroneMap/WebODM](https://webodm.org/) |
| **LichtFeld Studio** | 3D Gaussian Splatting fotorrealista | `lichtfeld.sh` ✅ | [lichtfeld.io](https://lichtfeld.io/) |
| **SuperSplat** | Editor web de Gaussian Splats | `supersplat.sh` ✅ | [playcanvas/supersplat](https://github.com/playcanvas/supersplat) |

### Geração Procedural (Caminho B)
| Ferramenta | Função | Wrapper | Repo |
|------------|--------|---------|------|
| **WorldGen** | Text-to-3D scene (ZiYang-xie) | `worldgen.sh` ✅ | [ZiYang-xie/WorldGen](https://github.com/ZiYang-xie/WorldGen) |
| **TerraForge3D** | Terreno procedural GPU + node editor | `terraforge.sh` ✅ | [Jaysmito101/TerraForge3D](https://github.com/Jaysmito101/TerraForge3D) |
| **Terrain3D** | Sistema de terreno para Godot 4 | `terrain3d.sh` ✅ | [TokisanGames/Terrain3D](https://github.com/TokisanGames/Terrain3D) |
| **SimpleXTerrain** | Gerador procedural para Terrain3D | (via terrain3d.sh) | [prajwal-mx/SimpleXTerrain](https://github.com/prajwal-mx/SimpleXTerrain) |
| **GameFactory-3A** | gen_3d_scene / gen_3d_object | `gamefactory.sh` ✅ | [OpenDCAI/GameFactory-3A](https://github.com/OpenDCAI/GameFactory-3A) |
| **3DWorld** | Engine OpenGL clássica com geração | `3dworld.sh` ✅ | [fegennari/3DWorld](https://github.com/fegennari/3DWorld) |
| **Bycob/world** | Mundo voxel/infinito C++ | `bycob_world.sh` ✅ | [Bycob/world](https://github.com/Bycob/world) |
| **Terasology** | Engine voxel Java modular | `terasology.sh` ✅ | [MovingBlocks/Terasology](https://github.com/MovingBlocks/Terasology) |
| **rsgeotools** | OSM → 3D world real | `rsgeotools.sh` ✅ | [romanshuvalov/rsgeotools](https://github.com/romanshuvalov/rsgeotools) |

### Processamento
- **Blender** (headless, via Python) — retopologia, LODs, texturas PBR, exportação.
- **gltf-transform / gltflib** — validação e otimização GLB.

### Engine Alvo
- **Godot 4** (preferencial — 100% open source, Terrain3D + SimpleXTerrain nativos)
- **Unity 6** (via adapter)
- **Unreal Engine 5** (via plugin GaussianSplats3D)

---

## 🏛️ Arquitetura

```
                ┌──────────────────────────┐
                │   Entrada do Usuário     │
                │ (texto / fotos / drone / │
                │  OSM / voxel / coords)   │
                └────────────┬─────────────┘
                             ▼
                ┌──────────────────────────┐
                │   Agente Orquestrador    │
                │   (GameFactory-3A +      │
                │    Skills customizadas)  │
                └────────────┬─────────────┘
                             │
        ┌────────────┬───────┴────────┬──────────────┐
        ▼            ▼                ▼              ▼
   ┌─────────┐ ┌──────────┐    ┌──────────┐    ┌──────────┐
   │Caminho A│ │Caminho B │    │Caminho C │    │Caminho D │
   │ Recon   │ │Procedural│    │   OSM    │    │  Voxel   │
   └────┬────┘ └─────┬────┘    └─────┬────┘    └─────┬────┘
        │            │              │              │
   COLMAP/       WorldGen/      rsgeotools/    Bycob/Terasology
   AliceVision   TerraForge     terrain        (voxel massivo)
   WebODM        GameFactory
   LichtFeld
        │            │              │              │
        └────────────┴──────┬───────┴──────────────┘
                            ▼
                ┌──────────────────────────┐
                │ Processamento de Assets  │
                │ (Blender headless +      │
                │  retopologia / LOD /     │
                │  PBR / colisões)         │
                └────────────┬─────────────┘
                             ▼
                ┌──────────────────────────┐
                │  Montagem da Cena        │
                │  (Godot 4 preferencial)  │
                └────────────┬─────────────┘
                             ▼
                ┌──────────────────────────┐
                │ Validação + Iteração     │
                └──────────────────────────┘
```

---

## 📁 Estrutura do Repositório

```
ai-3d-world-pipeline/
├── README.md                  ← você está aqui
├── LICENSE                    ← MIT
├── .gitignore
├── ARCHITECTURE.md            ← detalhes técnicos
│
├── docs/                      ← documentação por caminho
│   ├── path-a-reconstruction.md
│   ├── path-b-procedural.md
│   ├── asset-processing.md
│   └── scene-assembly.md
│
├── skills/                    ← Skills do agente (8)
│   ├── orchestrator.md
│   ├── photogrammetry.md
│   ├── gaussian-splatting.md
│   ├── procedural-terrain.md
│   ├── worldgen.md
│   ├── osm-worldgen.md
│   ├── voxel-world.md
│   └── classical-3dworld.md
│
├── tools/                     ← wrappers CLI e Python
│   ├── README.md
│   ├── cli-wrappers/          ← 15 wrappers (todos reais)
│   └── python/
│
├── pipelines/                 ← 5 pipelines declarativos
│   ├── reconstruction.yaml
│   ├── procedural.yaml
│   ├── hybrid.yaml
│   ├── osm_world.yaml
│   └── voxel_world.yaml
│
├── examples/                  ← exemplos de uso
│   ├── drone-photos-to-splat.md
│   ├── text-to-world.md
│   └── digital-twin.md
│
├── outputs/                   ← artefatos (gitignored)
│
└── .github/workflows/
    └── validate.yml
```

---

## 🚀 Quick Start

```bash
# Clonar
git clone https://github.com/GrupoANDevelopment-m/ai-3d-world-pipeline.git
cd ai-3d-world-pipeline

# Caminho A — drone → splat
python tools/python/pipeline_runner.py \
    --pipeline pipelines/reconstruction.yaml \
    --var photos_dir=./input/drone/ \
    --var output_dir=./outputs/factory/

# Caminho B — prompt → mundo
python tools/python/pipeline_runner.py \
    --pipeline pipelines/procedural.yaml \
    --var prompt="Vila costeira com falésias" \
    --var biome=coastal

# Caminho C — OSM → cidade real
python tools/python/pipeline_runner.py \
    --pipeline pipelines/osm_world.yaml \
    --var tile_x=8580 --var tile_y=5611 --var cache_dir=/data/gpak

# Caminho D — voxel massivo
python tools/python/pipeline_runner.py \
    --pipeline pipelines/voxel_world.yaml \
    --var engine=bycob_world --var seed=42
```

---

## 📖 Documentação

- 📐 [Arquitetura Detalhada](ARCHITECTURE.md)
- 📸 [Caminho A — Reconstrução](docs/path-a-reconstruction.md)
- 🌍 [Caminho B — Procedural + AI](docs/path-b-procedural.md)
- 🧹 [Processamento de Assets](docs/asset-processing.md)
- 🎬 [Montagem da Cena](docs/scene-assembly.md)

### Skills do Agente
- 🧭 [Orchestrator](skills/orchestrator.md) — decide o caminho
- 📸 [Photogrammetry](skills/photogrammetry.md) — SfM + MVS
- ✨ [Gaussian Splatting](skills/gaussian-splatting.md) — LichtFeld + SuperSplat
- ⛰️ [Procedural Terrain](skills/procedural-terrain.md) — TerraForge3D / Terrain3D / Bycob
- 🪄 [WorldGen](skills/worldgen.md) — text-to-3D scene
- 🗺️ [OSM WorldGen](skills/osm-worldgen.md) — rsgeotools
- 🧊 [Voxel World](skills/voxel-world.md) — Bycob/world + Terasology
- 🌌 [Classical 3DWorld](skills/classical-3dworld.md) — fegennari/3DWorld

---

## 🧪 Validação e CI

Workflow `.github/workflows/validate.yml` valida a cada push:
- Sintaxe dos YAMLs em `pipelines/`
- Bash lint dos wrappers
- Python compile-check
- Front-matter das Skills
- Links do README

---

## 🤝 Como Contribuir

1. Fork → branch (`feat/nova-skill` ou `fix/wrapper-colmap`)
2. Adicione/atualize a Skill em `skills/`
3. Se ferramenta nova, crie wrapper em `tools/cli-wrappers/`
4. Adicione etapa no `pipelines/*.yaml`
5. PR descrevendo: caminho, entrada, saída, dependências

---

## 📜 Licença

MIT — use à vontade, comercial inclusive. Atribuição apreciada.

---

## ✨ Status Atual

- ✅ **15 wrappers CLI** implementados e funcionais (todos com help + log + meta.json)
- ✅ **8 Skills** documentadas com front-matter YAML
- ✅ **5 pipelines** declarativos (reconstruction, procedural, hybrid, osm_world, voxel_world)
- ✅ **3 helpers Python** (asset_processor, pipeline_runner, gltf_validator)
- ✅ **CI** validando estrutura a cada push

---

<p align="center">
Feito com ☕ + 🤖 por <a href="https://github.com/GrupoANDevelopment-m">GrupoANDevelopment-m</a>
</p>
