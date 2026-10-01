# Agent Framework — Integração LLM (Inspirado em DeepSeek Harness)

Inspirado em [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
(Cordis + dsh-tools + dsh-agent-loop), adaptado pra Python e **integrado com tudo
que já existe no repo** — sem reescrever nada.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│  User prompt / API                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  tools/agent/cli.py     ← entry point:  python3 -m tools.agent.cli │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  tools/agent/agent.py   ← ReactLoopAgent simplificado            │
│  Loop: LLM → tool_calls → executa → volta pro LLM                │
└─────────────────────────────────────────────────────────────────┘
            ↓                  ↓                   ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ tools/agent/    │  │ tools/agent/    │  │ tools/agent/    │
│ llm.py          │  │ tools.py        │  │ skills.py       │
│ (OpenAI-compat  │  │ (18 tools       │  │ (8 procedural   │
│ DeepSeek/OpenAI │  │  registradas    │  │  patterns injet.│
│ /custom/demo)   │  │  automaticamente│  │  como system    │
│                 │  │  dos wrappers)  │  │  prompt)        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
            ↓                  ↓
┌─────────────────┐  ┌─────────────────────────────────────────┐
│ tools/agent/    │  │ tools/cli-wrappers/  (15 .sh wrappers) │
│ session.py      │  │ tools/python/         (Python modules)  │
│ (JSONL append   │  │ pipelines/*.yaml      (composite)       │
│  only log)      │  │ skills/*.md           (procedural docs) │
└─────────────────┘  │ tools/colibri_patterns/ (JustVugg)      │
                     └─────────────────────────────────────────┘
```

## Tools registradas (18)

**Generation** (3):
- `bycob_world` → world procedural via Bycob C++
- `cubiquity_generate` → voxel world via Cubiquity
- `rsgeotools_generate` → cidade OSM via rsgeotools-rvtgen3d

**Processing** (3):
- `blender_process` → OBJ → GLB com LODs
- `terraforge` → editor GUI
- `asset_processor` → pipeline Python de assets

**Reconstruction** (2):
- `colmap_reconstruct` → SfM+MVS photogrammetry
- `opensplat_train` → 3DGS training CPU

**Analysis** (2):
- `gltf_validate` → valida .glb
- `libigl_analyze` → mesh analysis (16641 verts testado)

**Export** (1):
- `godot_build_scene` → projeto Godot 4 jogável

**Pipeline** (7): um por YAML em `pipelines/`
- `pipeline_hybrid`, `pipeline_osm_world`, `pipeline_procedural`,
  `pipeline_reconstruction`, `pipeline_verified_real`, `pipeline_voxel_world`,
  `pipeline_with_gpu_stage`

## Skills carregadas (8)

Lidas de `skills/*.md` automaticamente:
- `orchestrator`, `procedural-terrain`, `worldgen`, `voxel-world`,
  `osm-worldgen`, `photogrammetry`, `gaussian-splatting`, `classical-3dworld`

## Uso

### Status
```bash
python3 -m tools.agent.cli status
```

### Listar tools/skills
```bash
python3 -m tools.agent.cli tools
python3 -m tools.agent.cli skills
```

### One-shot prompt (demo mode sem API)
```bash
python3 -m tools.agent.cli "criar voxel world com cubiquity"
python3 -m tools.agent.cli "gerar terrain + blender + godot scene"
python3 -m tools.agent.cli "run pipeline verified_real"
```

### REPL interativo
```bash
python3 -m tools.agent.cli repl
> /tools
> /skills
> criar voxel world
> /quit
```

### Com API key real (LLM decide)
```bash
export DEEPSEEK_API_KEY=sk-xxx
# ou
export OPENAI_API_KEY=sk-xxx
# ou
export LLM_API_KEY=xxx LLM_BASE_URL=https://custom.endpoint LLM_MODEL=custom
python3 -m tools.agent.cli "criar mundo completo"
```

## Modos

| Provider | Trigger | Comportamento |
|----------|---------|---------------|
| `openai` | `OPENAI_API_KEY` set | OpenAI SDK, model `gpt-4o-mini` default |
| `deepseek` | `DEEPSEEK_API_KEY` set | DeepSeek SDK, model `deepseek-chat` default |
| `custom` | `LLM_API_KEY` set | OpenAI-compatible (Anthropic, Together, etc) |
| `demo` | nenhuma key | Heurística de intent + tool calling automático |

## Persistência

Cada session gera `/workspace/ai-3d-world-pipeline/outputs/sessions/<id>.jsonl`
contendo:
- `header` event
- `user` message
- `assistant` messages (com tool_calls)
- `tool_call` events
- `tool_result` events
- `error` events

Replay possível com `Session.load(path)`.

## Demo mode (sem API)

Sem API key, o demo mode detecta intent em palavras-chave:
- "voxel"/"minecraft"/"sponge" → cubiquity_generate
- "terrain"/"terreno"/"bycob" → bycob_world
- "blender"/"lod" → blender_process
- "godot"/"scene" → godot_build_scene
- "validate" → gltf_validate
- "pipeline"/"run" → pipeline_verified_real

Útil pra testar o agent loop end-to-end sem gastar tokens.

## Decisão de arquitetura

**O que copiei do dsh:**
- Tool registry com JSON Schema DSL
- ReactLoopAgent (LLM → tool → LLM)
- Skills como system prompt context
- Session append-only log
- Plugin philosophy ("everything is replaceable")

**O que ADAPTEI pro nosso contexto:**
- Python em vez de TypeScript (consistente com a pipeline)
- Tools descobrem wrappers/scripts existentes (não duplica)
- Skills carregam os .md já escritos como contexto
- Session persistence em JSONL (não precisa SQLite)
- Pipeline YAML existente vira "composite tool"

**O que NÃO copiei:**
- Cordis framework (overhead, não precisamos)
- Typert type graph (pydantic já dá conta)
- E2B sandbox (não temos cloud)
- Web UI (CLI/REPL basta por enquanto)

## Próximos passos quando APIs LLM forem fornecidas

1. Setar `DEEPSEEK_API_KEY` (recomendado - barato, bom)
2. Rodar REPL ou one-shot
3. LLM vai REALMENTE planejar e chamar tools baseado nos outputs
4. Tools existentes já funcionam (verificado testando cada uma)
5. Pipeline end-to-end real: prompt → LLM decide → tools rodam → output real

**Tudo reutilizado**: wrappers, skills, pipelines, tools Python, Colibri patterns.
Nenhum arquivo existente foi reescrito.
