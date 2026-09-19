---
name: orchestrator
version: 0.3.0
triggers:
  - "criar mundo 3d"
  - "gerar cena"
  - "digital twin"
  - "montar cena"
  - "build scene"
  - "recreate real place"
  - "recriar lugar real"
  - "voxel world"
  - "minecraft style"
inputs:
  required:
    - raw_input: string | object
  optional:
    - intent: reconstruction | procedural | osm | voxel | hybrid | auto
    - engine_target: godot4 | unity6 | ue5
    - max_polycount: int
    - target_fps: int
    - geographic_accuracy_cm: int
outputs:
  type: scene
  format: godot | unity | ue5 | splat
calls:
  - tool: any
    method: pipeline_runner
fallbacks:
  - if: gpu_unavailable
    then: use_cpu_path
  - if: tool_missing
    then: log_and_skip_stage
---

# 🧭 Skill: Orchestrator

Habilidade central. Decide **qual caminho seguir** e **quais Skills delegar**.

---

## Caminhos disponíveis

| Path | Quando | Skills principais |
|------|--------|-------------------|
| **A — Reconstruction** | Fotos / vídeo / drone | photogrammetry → gaussian-splatting |
| **B — Procedural + AI** | Prompt / imagem criativa | worldgen → procedural-terrain → gamefactory |
| **C — OSM Real** | Recriar lugar real (cidade, rua) | osm-worldgen → procedural-terrain |
| **D — Voxel / Infinito** | Mundo estilo Minecraft massivo | voxel-world (bycob ou terasology) |
| **E — Clássico OpenGL** | Render fotorrealista legacy | classical-3dworld |
| **HYBRID** | Combina 2+ caminhos acima | mix |

---

## Como o agente usa

```
Usuário: "Crie um digital twin de uma fábrica a partir destas 120 fotos
          de drone + um terreno montanhoso procedural de 1 km² ao redor"

Orquestrador:
1. intent=hybrid (drone_photos + prompt)
2. Caminho A → Skill photogrammetry → Skill gaussian-splatting (LichtFeld)
3. Caminho B → Skill procedural-terrain (TerraForge3D)
4. Skill asset-processing (Blender headless)
5. Skill scene-assembly (Godot 4)
6. Validação + relatório
```

---

## Algoritmo de Decisão

```python
def route(raw_input, intent="auto") -> str:
    if intent == "auto":
        intent = auto_detect(raw_input)

    has_media   = has_photos(raw_input) or has_video(raw_input)
    has_prompt  = has_text_prompt(raw_input)
    has_osm     = has_osm_bbox(raw_input) or has_tile_coords(raw_input)
    has_voxel   = mentions_voxel(raw_input) or mentions_minecraft(raw_input)

    if intent == "hybrid":               return "HYBRID"
    if intent == "osm":                  return "PATH_C_OSM"
    if intent == "voxel":                return "PATH_D_VOXEL"
    if intent == "classical":            return "PATH_E_CLASSICAL"

    if has_media and has_prompt:         return "HYBRID"
    if has_media:                        return "PATH_A_RECONSTRUCTION"
    if has_voxel:                        return "PATH_D_VOXEL"
    if has_osm:                          return "PATH_C_OSM"
    if has_prompt:                       return "PATH_B_PROCEDURAL"
    raise ValueError("Não foi possível determinar o caminho")
```

---

## Contrato de Entrada

```json
{
  "request_id": "uuid",
  "raw_input": {
    "photos_dir": "./drone_photos/",
    "video_path": null,
    "prompt": "Vila costeira portuguesa com falésias e farol",
    "reference_image": "./refs/coastal.jpg",
    "osm_bbox": [38.7, -9.1, 38.8, -9.0],
    "osm_tile": [8580, 5611],
    "voxel": false,
    "engine": "godot4"
  },
  "intent": "auto",
  "constraints": {
    "engine_target": "godot4",
    "max_polycount": 500000,
    "target_fps": 60,
    "geographic_accuracy_cm": null
  }
}
```

---

## Contrato de Saída

```json
{
  "request_id": "uuid",
  "status": "ok | error | partial",
  "path_taken": "HYBRID",
  "artifacts": {
    "splat": "./outputs/.../scene.ksplat",
    "mesh": "./outputs/.../mesh.glb",
    "heightmap": "./outputs/.../heightmap.png",
    "osm_city": "./outputs/.../city.obj",
    "project_root": "./outputs/.../scene.godot/"
  },
  "report": {
    "validation_passed": true,
    "fps_measured": 72,
    "polycount_total": 312000,
    "warnings": [],
    "errors": []
  }
}
```

---

## Telemetria

Cada execução gera log estruturado em `outputs/<run_id>/telemetry.jsonl`.

---

## Próximos passos

1. Você me fornece links dos frameworks não cobertos (se houver).
2. Eu adiciono Skills e atualizo pipelines.
3. Tests + CI rodando automaticamente a cada push.
