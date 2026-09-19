# 🎬 Montagem da Cena & Caminho Híbrido

> Como o agente monta a cena final na engine alvo e como combinar Caminho A + Caminho B.

---

## Caminho Híbrido (A + B)

É o caso mais poderoso: **digital twin com elementos criativos**.

```
[120 fotos drone da fábrica]
        │
        ▼  (Caminho A)
[Splat fotorrealista da fábrica]
        │
        │ + [prompt: "terreno montanhoso 1 km² ao redor"]
        ▼  (Caminho B)
[Terreno procedural montanhoso]
        │
        ▼
[Composição no Godot 4]
        │
        ▼
[Projeto .godot/ pronto]
```

---

## Composição no Godot 4

```gdscript
# scripts/orchestrator/assemble_scene.gd
@tool
extends Node3D

@export var splat_path: String
@export var terrain_path: String
@export var props_paths: Array[String] = []

func assemble():
    # 1. Carrega splat (Caminho A)
    var splat = preload("res://addons/gsplat/splat_viewport.tscn").instantiate()
    splat.set_splat_file(splat_path)
    add_child(splat)

    # 2. Carrega terreno (Caminho B)
    var terrain = preload("res://scenes/terrain.tscn").instantiate()
    terrain.load_heightmap(terrain_path)
    add_child(terrain)

    # 3. Espalha props
    for p in props_paths:
        var prop = load(p).instantiate()
        add_child(prop)
        # usa FastNoiseLite + PCG para distribuição

    # 4. Lighting & atmosfera
    var env := Environment.new()
    env.background_mode = Environment.BG_SKY
    env.ambient_light_color = Color(0.3, 0.35, 0.4)
    get_viewport().world_3d.environment = env
```

---

## Cena Final Esperada

```
outputs/factory_digital_twin/
├── scene.godot/
│   ├── project.godot
│   ├── scenes/
│   │   ├── main.tscn
│   │   ├── splat_fabrica.tscn
│   │   ├── terrain_montanha.tscn
│   │   └── props/
│   ├── assets/
│   │   ├── splats/fabrica.spz
│   │   ├── terrain/heightmap.png
│   │   └── props/
│   └── scripts/orchestrator/
└── report.json  ← validação + métricas
```

---

## Adapters para Unity / UE5

Mesma estrutura de saída, com adapter:

| Engine | Adapter | Saída |
|--------|---------|-------|
| Godot 4 | nativo | `.tscn` + `.tres` + `.glb` |
| Unity 6 | `unity-adapter` | `.unity` + `.prefab` + `.glb` |
| UE5 | `ue5-adapter` | `.umap` + `.uasset` + `.glb` |

Em Godot, o Terrain3D + SimpleXTerrain dão o melhor resultado com **zero licença** e suporte completo a **LODs e splat blending**.

---

## Iluminação & Atmosfera

| Estilo | Solução |
|--------|---------|
| Dia ensolarado | `DirectionalLight3D` + `WorldEnvironment` c/ `BG_SKY` |
| Pôr-do-sol | mesmo + god-rays (EffectComposer) |
| Noite | `DirectionalLight3D` (baixo) + OmniLights espalhados |
| Interior HDR | HDRi cubemap + IBL |

A Skill `lighting` (em `skills/`) lê o `prompt` e escolhe o preset.

---

## Checklist Final (validação automática)

- [ ] `gltf-validator` aprova todos os assets
- [ ] FPS ≥ alvo (60 padrão)
- [ ] `max_polycount` respeitado
- [ ] Colliders atribuídos em todos os estáticos
- [ ] Câmera principal com `position` válida
- [ ] `Environment` configurado (não preto)
- [ ] `report.json` gerado

Se algum item falhar → orquestrador decide se itera (volta ao estágio correspondente) ou aborta.
