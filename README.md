# AI 3D World Pipeline 🌍🤖

> Pipeline orquestrado por IA para geração e reconstrução de mundos 3D — unificando fotogrametria, Gaussian Splatting, geração procedural e integração com engines (Godot 4 / Unity / UE5).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Engine: Godot 4](https://img.shields.io/badge/Engine-Godot%204-478CBF?logo=godot-engine)](https://godotengine.org/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org/)
[![Open Source](https://img.shields.io/badge/100%25-Open%20Source-brightgreen)]()

---

## 🎯 O que é

Um **pipeline modular e extensível** que permite a um **Coding Agent / Multi-Agent** (Claude Code, Codex, GameFactory-3A, ou agente customizado em LangGraph / CrewAI) decidir automaticamente entre dois caminhos:

- **Caminho A — Reconstrução**: fotos / vídeos / drone → mesh + Gaussian Splat fotorrealista.
- **Caminho B — Geração Procedural + AI**: prompt / imagem de referência → mundo 3D completo.

O resultado é montado, validado e exportado para a engine alvo. Tudo **100% open source**.

---

## 🏛️ Arquitetura

```
                ┌──────────────────────────┐
                │   Entrada do Usuário     │
                │ (texto / fotos / drone / │
                │  OSM / imagem / specs)   │
                └────────────┬─────────────┘
                             ▼
                ┌──────────────────────────┐
                │   Agente Orquestrador    │
                │   (GameFactory-3A +      │
                │    Skills customizadas)  │
                └────────────┬─────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
       ┌────────────────┐        ┌────────────────┐
       │   Caminho A    │        │   Caminho B    │
       │ Reconstrução   │        │  Procedural    │
       │ (dados reais)  │        │  + AI          │
       └────────┬───────┘        └────────┬───────┘
                ▼                         ▼
       COLMAP / Meshroom           WorldGen /
       WebODM                      TerraForge3D /
       LichtFeld (3DGS)            Terrain3D /
                                   GameFactory-3A
                │                         │
                └────────────┬────────────┘
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
                │ (testes automatizados,   │
                │  relatório de qualidade) │
                └──────────────────────────┘
```

---

## 📁 Estrutura do Repositório

```
ai-3d-world-pipeline/
├── README.md                  ← você está aqui
├── LICENSE                    ← MIT
├── .gitignore
├── ARCHITECTURE.md            ← detalhes técnicos da arquitetura
│
├── docs/                      ← documentação por etapa
│   ├── path-a-reconstruction.md
│   ├── path-b-procedural.md
│   ├── asset-processing.md
│   └── scene-assembly.md
│
├── skills/                    ← Skills do agente orquestrador
│   ├── orchestrator.md
│   ├── photogrammetry.md
│   ├── gaussian-splatting.md
│   ├── procedural-terrain.md
│   └── worldgen.md
│
├── tools/                     ← wrappers CLI e Python
│   ├── README.md
│   ├── cli-wrappers/
│   │   ├── colmap.sh
│   │   ├── meshroom.sh
│   │   ├── webodm.sh
│   │   └── lichtfeld.sh
│   └── python/
│       └── asset_processor.py
│
├── pipelines/                 ← definições declarativas de pipeline
│   ├── reconstruction.yaml
│   ├── procedural.yaml
│   └── hybrid.yaml
│
├── examples/                  ← exemplos completos de uso
│   ├── drone-photos-to-splat.md
│   ├── text-to-world.md
│   └── digital-twin.md
│
├── outputs/                   ← onde os artefatos finais caem (gitignored)
│   └── README.md
│
└── .github/workflows/         ← CI para validação automática
    └── validate.yml
```

---

## 🚀 Quick Start

### 1. Pré-requisitos

- Python 3.10+
- Docker (recomendado para isolar ferramentas pesadas)
- GPU NVIDIA com CUDA (para COLMAP / 3DGS — opcional mas recomendado)
- Godot 4.x (engine alvo preferencial)

### 2. Clonar o pipeline

```bash
git clone https://github.com/GrupoANDevelopment-m/ai-3d-world-pipeline.git
cd ai-3d-world-pipeline
```

### 3. Configurar o agente

O pipeline é **agnóstico de agente**. Use qualquer um destes como orquestrador:

| Agente | Como integrar |
|--------|--------------|
| **GameFactory-3A** | Carregue as Skills em `skills/` e registre os operadores de `tools/` |
| **Claude Code / Codex** | Aponte para `ARCHITECTURE.md` + `skills/` como contexto |
| **LangGraph / CrewAI** | Importe `tools/python/` e construa grafo de agentes |
| **Custom CLI** | Use `tools/cli-wrappers/*.sh` como entry points |

### 4. Rodar um exemplo

```bash
# Caminho A: drone → splat fotorrealista
python tools/python/asset_processor.py --pipeline pipelines/reconstruction.yaml \
    --input ./drone_photos/ --output outputs/factory_splat/

# Caminho B: prompt → mundo procedural
python tools/python/asset_processor.py --pipeline pipelines/procedural.yaml \
    --prompt "Vila costeira com falésias e farol" --output outputs/coastal_village/
```

---

## 🛠️ Ferramentas Integradas

### Reconstrução (Caminho A)
| Ferramenta | Função | Status |
|------------|--------|--------|
| [COLMAP](https://colmap.github.io/) | Structure-from-Motion + Dense MVS | ✅ wrapper pronto |
| [Meshroom (AliceVision)](https://alicevision.org/) | Pipeline SfM alternativo | ✅ wrapper pronto |
| [WebODM](https://www.opendronemap.org/webodm/) | Ortofotos, DEM, nuvem georreferenciada (drone) | ✅ wrapper pronto |
| [LichtFeld Studio](https://github.com/RobertKrajewski/LichtFeld-Studio) | 3D Gaussian Splatting fotorrealista em tempo real | ✅ wrapper pronto |

### Geração Procedural (Caminho B)
| Ferramenta | Função | Status |
|------------|--------|--------|
| [WorldGen](https://github.com/microsoft/WorldGen) | Geração de cena 3D a partir de texto/imagem | 🔌 aguardando link do framework |
| TerraForge3D | Terreno procedural de alta qualidade | 🔌 aguardando link do framework |
| SimpleXTerrain + Terrain3D | Terreno nativo para Godot 4 | 🔌 aguardando link do framework |
| GameFactory-3A | Operadores `gen_3d_scene` / `gen_3d_object` | 🔌 aguardando link do framework |
| rsgeotools | Mundos baseados em OpenStreetMap | 🔌 aguardando link do framework |
| 3DWorld / Bycob/world | Geração avançada de vegetação e cidades | 🔌 aguardando link do framework |

> **Próximo passo**: o usuário fornecerá os links dos frameworks que ficaram marcados como "aguardando" — eles serão plugados em `tools/cli-wrappers/` e `tools/python/`.

### Processamento
- **Blender** (headless, via Python) — retopologia, LODs, texturas PBR, exportação.
- **InstaMesh / MeshLab** (opcional) — limpeza de mesh.

### Engine Alvo
- **Godot 4** (preferencial — 100% open source, Terrain3D + SimpleXTerrain nativos)
- **Unity 6** (via adapter)
- **Unreal Engine 5** (via plugin)

---

## 🧠 Como o Agente Decide o Caminho

```python
# Pseudocódigo do orquestrador (skills/orchestrator.md)
def route(user_input):
    if user_input.has("drone_photos") or user_input.has("video") or user_input.has("photo_set"):
        return "PATH_A_RECONSTRUCTION"
    elif user_input.has("prompt") or user_input.has("reference_image"):
        if user_input.requires("real_geography"):
            return "PATH_B_WITH_OSM"
        return "PATH_B_PROCEDURAL"
    elif user_input.has("both"):
        return "PATH_HYBRID"
```

A regra completa com fallbacks está em [`skills/orchestrator.md`](skills/orchestrator.md).

---

## 📖 Documentação

- 📐 [Arquitetura Detalhada](ARCHITECTURE.md)
- 📸 [Caminho A — Reconstrução](docs/path-a-reconstruction.md)
- 🌍 [Caminho B — Procedural + AI](docs/path-b-procedural.md)
- 🧹 [Processamento de Assets](docs/asset-processing.md)
- 🎬 [Montagem da Cena](docs/scene-assembly.md)

### Skills do Agente
- 🧭 [Orchestrator](skills/orchestrator.md)
- 📸 [Photogrammetry](skills/photogrammetry.md)
- ✨ [Gaussian Splatting](skills/gaussian-splatting.md)
- ⛰️ [Procedural Terrain](skills/procedural-terrain.md)
- 🪄 [WorldGen (text-to-3D)](skills/worldgen.md)

---

## 🧪 Validação e CI

Toda modificação passa pelo workflow `.github/workflows/validate.yml`, que:
1. Valida a sintaxe dos YAMLs em `pipelines/`.
2. Linta os scripts Python e shell.
3. Confere que os CLIs declarados existem.
4. Gera um relatório de saúde do pipeline.

---

## 🤝 Como Contribuir

1. Fork → branch (`feat/nova-skill` ou `fix/wrapper-colmap`).
2. Adicione / atualize a Skill correspondente em `skills/`.
3. Se for ferramenta nova, crie o wrapper em `tools/cli-wrappers/` e teste localmente.
4. Abra PR descrevendo: caminho (A/B/Híbrido), entrada, saída, dependências.

---

## 📜 Licença

MIT — use à vontade, comercial inclusive. Atribuição apreciada.

---

## ✨ Roadmap

- [ ] Integração WorldGen / TerraForge3D (aguardando link)
- [ ] Adapter Godot 4 com Terrain3D + SimpleXTerrain
- [ ] Adapter Unity 6 (HumanTechLLM / Meshy)
- [ ] Adapter UE5 (Quixel + Nanite)
- [ ] Self-test do agente (LangGraph eval)
- [ ] Dashboard web de monitoramento de pipelines

---

<p align="center">
Feito com ☕ + 🤖 por <a href="https://github.com/GrupoANDevelopment-m">GrupoANDevelopment-m</a>
</p>
