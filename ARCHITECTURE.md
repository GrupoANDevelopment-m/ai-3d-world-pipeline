# 📐 Arquitetura Detalhada

> Documento técnico de referência para o pipeline. Lido pelo agente orquestrador.

---

## 1. Modelo de Camadas

O pipeline é dividido em **6 camadas**. Cada camada só conversa com a camada imediatamente abaixo — o que mantém o sistema auditável e substituível.

```
┌─────────────────────────────────────────────────────────┐
│ Camada 6 — Validação & Iteração (CI, relatórios, QA)   │
├─────────────────────────────────────────────────────────┤
│ Camada 5 — Exportação (Godot / Unity / UE5 / Blender)  │
├─────────────────────────────────────────────────────────┤
│ Camada 4 — Montagem da Cena (assembly, lighting, FX)   │
├─────────────────────────────────────────────────────────┤
│ Camada 3 — Processamento de Assets (retopo, LOD, PBR)  │
├─────────────────────────────────────────────────────────┤
│ Camada 2 — Geração (A: reconstrução / B: procedural)   │
├─────────────────────────────────────────────────────────┤
│ Camada 1 — Entrada & Interpretação (prompt / fotos)    │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Camada 1 — Entrada & Interpretação

Aceita:

| Tipo | Exemplo | Detector |
|------|---------|----------|
| Texto | "Vila costeira com falésias" | `prompt` no input |
| Fotos | 120 fotos drone de fábrica | `.jpg/.jpeg/.png` em diretório |
| Vídeo | `drone_flythrough.mp4` | arquivo `.mp4/.mov` |
| OSM | bbox `[lat, lon, lat, lon]` | campo `osm_bbox` |
| Imagem de referência | `reference.jpg` + `prompt` | campo `reference_image` |
| Specs de engenharia | "2 km², precisão 5cm" | campo `engineering_spec` |

**Saída normalizada**: objeto `PipelineRequest` em JSON:

```json
{
  "request_id": "uuid",
  "intent": "reconstruction | procedural | hybrid",
  "inputs": { ... },
  "constraints": {
    "engine_target": "godot4",
    "max_polycount": 500000,
    "real_time_fps": 60,
    "geographic_accuracy_cm": 5
  }
}
```

---

## 3. Camada 2 — Geração (Roteamento)

### Decisor

```python
def decide_path(req: PipelineRequest) -> Path:
    if req.intent == "reconstruction":
        return Path.A
    if req.intent == "procedural":
        return Path.B
    if req.intent == "hybrid":
        return Path.HYBRID
    # auto-detect
    if req.inputs.has_media_files():
        return Path.A
    if req.inputs.has_text_prompt():
        return Path.B
    raise ValueError("Não foi possível determinar o caminho")
```

### Caminho A — Reconstrução

```
[Sparse SfM] → COLMAP / AliceVision (CLI) / Meshroom (GUI)
       ↓
[Dense MVS / MDE] → COLMAP dense OR WebODM (drone georrefer.)
       ↓
[Representação visual] → LichtFeld Studio (3D Gaussian Splatting)
       ↓
[Edição / Inspeção] → SuperSplat (PlayCanvas editor web)
       ↓
[Opcional] Extração de mesh do splat (para física/colisão)
```

Ver detalhes em [`docs/path-a-reconstruction.md`](docs/path-a-reconstruction.md).

### Caminho B — Geração Procedural + AI

```
[WorldGen ZiYang-xie] → cena base a partir de prompt/imagem
       ↓
[Terreno] → TerraForge3D OU SimpleXTerrain/Terrain3D (Godot) OU Bycob/world
       ↓
[Objetos] → GameFactory-3A (gen_3d_scene + gen_3d_object)
       ↓
[Opcional: engine clássica] → 3DWorld (fegennari) com configs específicas
```

Ver detalhes em [`docs/path-b-procedural.md`](docs/path-b-procedural.md).

### Caminho C — OSM Real (cidades e geografia reais)

```
[Tile coords OSM zoom 14] → rsgeotools-rvtgen3d
       ↓
[9 camadas: surface, buildings, roads, naturals, props, wires, etc.]
       ↓
[Opcional: terreno procedural sobreposto] → TerraForge3D
```

Ver detalhes em [`skills/osm-worldgen.md`](skills/osm-worldgen.md).

### Caminho D — Voxel / Infinito

```
[Bycob/world C++] OU [Terasology Java/Gradle]
       ↓
[Mundo massivo voxel com LOD automático, exploração ilimitada]
```

Ver detalhes em [`skills/voxel-world.md`](skills/voxel-world.md).

---

## 4. Camada 3 — Processamento de Assets

Padronização universal antes da montagem:

| Operação | Ferramenta | Quando aplicar |
|----------|-----------|----------------|
| Retopologia | Blender (Python headless) | Sempre que mesh > 500k tri |
| LODs | Blender / Instant Meshes | Sempre |
| Textura PBR | Blender / Substance (alternativa) | Para assets de Path B |
| Colisão | Blender → TriMesh | Para assets estáticos |
| Conversão | `gltf-transform` | GLB ↔ FBX ↔ OBJ |
| Validação | gltf-validator | Antes de exportar |

Implementação: [`tools/python/asset_processor.py`](tools/python/asset_processor.py).

---

## 5. Camada 4 — Montagem da Cena

A cena é montada em Godot 4 (preferencial). O agente gera um projeto `.godot/` com:

```
projeto/
├── project.godot
├── scenes/
│   ├── main.tscn
│   ├── terrain.tscn
│   ├── props/
│   └── lighting/
├── assets/
│   ├── terrain/
│   ├── props/
│   └── splats/
└── scripts/
    └── autoload/
```

Adapters para Unity 6 / UE5 são plugáveis em `tools/python/adapters/`.

---

## 6. Camada 5 — Exportação

Engine alvo + formato:

| Engine | Formato | Adapter |
|--------|---------|---------|
| Godot 4 | `.tscn` + `.tres` + `.glb` | nativo |
| Unity 6 | `.unity` + `.prefab` + `.glb` | `unity-adapter` |
| UE5 | `.umap` + `.uasset` + `.glb` | `ue5-adapter` (Nanite) |

---

## 7. Camada 6 — Validação

- Render headless (frame de teste).
- Performance (FPS mínimo exigido).
- Colisão (ray-cast em pontos críticos).
- Conformidade com constraint de `max_polycount`.
- Relatório JSON em `outputs/<run_id>/report.json`.

---

## 8. Skill Schema (formato das Skills)

Cada arquivo em `skills/` segue este formato:

```yaml
---
name: nome-da-skill
version: 0.1.0
triggers:
  - "palavra-chave 1"
  - "palavra-chave 2"
inputs:
  required: [...]
  optional: [...]
outputs:
  type: mesh | splat | heightmap | scene
  format: glb | ply | splat | godot
calls:
  - tool: colmap | meshroom | webodm | lichtfeld | terraforge | worldgen | blender
    method: cli | python | docker
fallbacks:
  - if: <condition>
    then: <alternative_tool>
---

# Documentação em markdown
```

O orquestrador lê esse front-matter e registra a skill automaticamente.

---

## 9. Versionamento e Compatibilidade

- Pipeline YAML: `semver`.
- Skills: `0.x.y` enquanto em desenvolvimento.
- Tools: fixadas por SHA do commit upstream.

---

## 10. Modos de Execução

| Modo | Comando | Quando usar |
|------|---------|-------------|
| Local | `python tools/python/asset_processor.py --pipeline X` | Dev / debug |
| Docker | `docker compose -f tools/docker-compose.yml up` | Isolamento |
| Cluster | via SLURM / K8s | Jobs pesados (3DGS em dataset grande) |
| Agente | `claude-code --pipeline X` ou via GameFactory-3A | IA autônoma |
