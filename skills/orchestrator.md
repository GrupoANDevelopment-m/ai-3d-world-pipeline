---
name: orchestrator
version: 0.1.0
triggers:
  - "criar mundo 3d"
  - "gerar cena"
  - "digital twin"
  - "montar cena"
  - "build scene"
inputs:
  required:
    - raw_input: string | object
  optional:
    - intent: reconstruction | procedural | hybrid | auto
    - engine_target: godot4 | unity6 | ue5
    - max_polycount: int
    - target_fps: int
outputs:
  type: scene
  format: godot | unity | ue5
calls:
  - tool: photogrammetry
    method: conditional
  - tool: worldgen
    method: conditional
  - tool: godot_adapter
    method: python
fallbacks:
  - if: gpu_unavailable
    then: use_cpu_path
  - if: tool_missing
    then: log_and_skip_stage
---

# 🧭 Skill: Orchestrator

Habilidade central. Decide **qual caminho seguir** (A / B / Híbrido) e **quais Skills delegar**.

---

## Como o agente usa

```
Usuário: "Crie um digital twin de uma fábrica a partir destas 120 fotos
          de drone + um terreno montanhoso procedural de 1 km² ao redor"

Orquestrador:
1. Detecta intent → hybrid (drone_photos + prompt)
2. Decide:
   - Ativa Skill photogrammetry nas 120 fotos (COLMAP + LichtFeld)
   - Ativa Skill procedural-terrain com prompt (TerraForge3D)
3. Ativa Skill asset-processing (Blender headless) em ambos
4. Ativa Skill scene-assembly (Godot 4) integrando splat + terreno
5. Roda validação + gera relatório
```

---

## Algoritmo de Decisão

```python
def route(raw_input, intent="auto") -> str:
    if intent == "auto":
        intent = auto_detect(raw_input)

    has_media = has_photos(raw_input) or has_video(raw_input)
    has_prompt = has_text_prompt(raw_input)
    has_osm = has_osm_bbox(raw_input)

    if intent == "hybrid":
        return "HYBRID"
    if has_media and has_prompt:
        return "HYBRID"
    if has_media:
        return "A_RECONSTRUCTION"
    if has_prompt and has_osm:
        return "B_PROCEDURAL_WITH_OSM"
    if has_prompt:
        return "B_PROCEDURAL"
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
    "osm_bbox": null
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
    "splat": "./outputs/.../scene.spz",
    "mesh": "./outputs/.../mesh.glb",
    "heightmap": "./outputs/.../heightmap.png",
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

## Estados Internos

```
PENDING → RUNNING_SF → RUNNING_SPLAT → RUNNING_ASSEMBLY → DONE
            ↓              ↓                  ↓
          FAILED        FAILED             FAILED
```

Em caso de `FAILED`, o orquestrador escolhe automaticamente entre:

1. **Retry** (mesma Skill, com parâmetros ajustados).
2. **Fallback** (Skill alternativa, ver `fallbacks`).
3. **Abort** (reporta ao usuário).

---

## Telemetria

Cada execução gera um log estruturado:

```json
{
  "timestamp": "2026-09-19T14:36:12Z",
  "stage": "RUNNING_SPLAT",
  "skill": "gaussian-splatting",
  "duration_s": 312,
  "gpu_mem_mb": 4096,
  "iterations": 30000
}
```

Salvo em `outputs/<run_id>/telemetry.jsonl`.
