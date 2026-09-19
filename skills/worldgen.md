---
name: worldgen
version: 0.1.0
triggers:
  - "text to 3d"
  - "text to world"
  - "gerar mundo de prompt"
  - "world generation"
  - "scene from text"
inputs:
  required:
    - prompt: string
  optional:
    - reference_image: string
    - style: realistic | stylized | anime | lowpoly
    - resolution: [int, int]
    - seed: int
outputs:
  type: scene
  format: glb | godot | unity
calls:
  - tool: worldgen
    method: python_api
  - tool: gamefactory
    method: python_api
fallbacks:
  - if: worldgen_unavailable
    then: gamefactory_only
  - if: prompt_too_vague
    then: ask_user_clarification
---

# 🪄 Skill: WorldGen (text-to-3D)

Gera cena 3D completa a partir de prompt em linguagem natural.

---

## Quando o agente ativa

- Input contém `prompt` (linguagem natural).
- Não há dados de captura reais (caso contrário, Caminho A).
- Criatividade é prioridade sobre fidelidade.

---

## Pipeline

```
[Prompt] + [reference_image opcional]
        │
        ▼
[WorldGen] → cena base (skybox, lighting, objetos grandes)
        │
        ▼
[GameFactory-3A] → objetos detalhados + scattering
        │
        ▼
[Cena montada em GLB]
```

---

## Exemplo de Uso

```python
from worldgen import SceneGenerator
from gamefactory import GameFactory

# 1. Cena base
gen = SceneGenerator(model="worldgen-xl")
base = gen.generate(
    prompt="Vila costeira portuguesa com falésias e farol ao entardecer",
    style="realistic",
    reference_image="./refs/coastal.jpg",  # opcional
    seed=42,
    resolution=(1920, 1080)
)

# 2. Detalhes + scattering
gf = GameFactory()
scene = gf.gen_3d_scene(
    prompt="Vila costeira portuguesa com falésias e farol",
    density="high",
    biome="mediterranean",
    bounds=base.bounds,
    base_scene=base,
    output="./output/coastal/scene.glb"
)
```

---

## Estilos Suportados

| Estilo | Quando usar | Engine hint |
|--------|-------------|-------------|
| realistic | jogos AAA, simulação | PBR 4K, ray tracing |
| stylized | jogos indie, mobile | PBR 1K, cel-shading |
| anime | visual novel, JRPG | toon shader |
| lowpoly | mobile, WebGL | flat shading, 512px |

---

## Interpretação do Prompt

WorldGen aplica um **parser semântico** para extrair:

```json
{
  "objects": ["farol", "casas", "falésias"],
  "attributes": {
    "lighting": "entardecer",
    "biome": "costeiro",
    "style": "português"
  },
  "scene_constraints": {
    "size_km": 2,
    "weather": "limpo",
    "time_of_day": "dusk"
  }
}
```

Se confiança < 0.6, a Skill pode pedir clarificação ao usuário.

---

## Comparação com outros modelos text-to-3D

| Modelo | Velocidade | Qualidade | Open Source |
|--------|-----------|-----------|-------------|
| WorldGen (Microsoft) | médio | alta | ✅ |
| Genie (Google) | lento | altíssima | ❌ (research only) |
| Meshy | rápido | média | ❌ (API paga) |
| GameFactory-3A (op) | rápido | boa | ✅ |
| TripoSR | muito rápido | média | ✅ |
| LRM (Large Rec. Model) | lento | alta | ✅ |

---

## Pós-processamento

```python
from tools.asset_processor import post_process

post_process(
    scene_path="./output/coastal/scene.glb",
    target_polycount=200_000,
    lod_levels=4,
    colliders=True,
    atlas_pbr=True
)
```

---

## Saída

```json
{
  "scene": "./output/coastal/scene.glb",
  "props": [
    "./output/coastal/props/lighthouse.glb",
    "./output/coastal/props/house_01.glb"
  ],
  "lighting_setup": {
    "sun": "dusk",
    "ambient": "warm_low"
  },
  "polycount_total": 187_500
}
```

Encaminha para `skills/scene-assembly.md`.
