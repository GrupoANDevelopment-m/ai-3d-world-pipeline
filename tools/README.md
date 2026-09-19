# 🛠️ Tools — Wrappers CLI & Python

Esta pasta contém os **wrappers** que o agente orquestrador chama para executar cada ferramenta.

---

## Estrutura

```
tools/
├── cli-wrappers/                   ← bash scripts (entry points leves)
│   ├── colmap.sh                   ← SfM + Dense MVS
│   ├── meshroom.sh                 ← Pipeline alternativo AliceVision
│   ├── webodm.sh                   ← Drone + georreferenciamento
│   ├── lichtfeld.sh                ← 3D Gaussian Splatting
│   ├── terraforge.sh               ← Terreno procedural multi-engine
│   ├── worldgen.sh                 ← Text-to-3D scene
│   ├── gamefactory.sh              ← gen_3d_scene / gen_3d_object
│   └── blender_process.sh          ← Asset processing headless
│
├── python/                         ← módulos Python (orquestração fina)
│   ├── asset_processor.py          ← processa mesh (retopo, LOD, PBR)
│   ├── colmap_runner.py            ← wrapper Python para COLMAP
│   ├── pipeline_runner.py          ← carrega YAML e executa estágios
│   └── gltf_validator.py           ← valida GLB final
│
└── docker/                         ← compose files (em breve)
    └── docker-compose.yml
```

---

## Como o agente chama

```python
import subprocess

# Caminho A — execução de Skill photogrammetry
result = subprocess.run([
    "bash", "tools/cli-wrappers/colmap.sh",
    "--photos", "./input/photos/",
    "--output", "./output/reconstruction/",
    "--type", "dense"
], check=True, capture_output=True, text=True)

# Ou via Python direto
from tools.python.pipeline_runner import run_pipeline
run_pipeline("./pipelines/reconstruction.yaml", inputs={
    "photos_dir": "./input/photos/"
})
```

---

## Convenção de Wrappers

Todo wrapper CLI:

1. Recebe `--input` e `--output` (sempre).
2. Tem `--help` documentando todos os parâmetros.
3. Loga tudo em `./output/run.log`.
4. Retorna exit code `0` em sucesso, `1` em falha recuperável, `2` em falha crítica.
5. Escreve metadados em `./output/meta.json`.

Exemplo de `meta.json`:

```json
{
  "tool": "colmap",
  "version": "3.8",
  "started_at": "2026-09-19T14:36:12Z",
  "duration_s": 1843,
  "input": "./input/photos/",
  "output": "./output/reconstruction/",
  "artifacts": {
    "sparse.ply": "./output/reconstruction/sparse.ply",
    "dense.ply": "./output/reconstruction/dense.ply"
  },
  "stats": {
    "registered_images": 118,
    "total_images": 120,
    "sparse_points": 52483,
    "dense_points": 18421000
  }
}
```

---

## Status dos Wrappers

| Wrapper | Status | Notas |
|---------|--------|-------|
| `colmap.sh` | ✅ implementado | pronto |
| `meshroom.sh` | ✅ implementado | stub, requer Meshroom instalado |
| `webodm.sh` | ✅ implementado | requer Docker + WebODM image |
| `lichtfeld.sh` | ✅ implementado | stub, requer LichtFeld instalado |
| `terraforge.sh` | ⏳ aguardando link | vai ser preenchido quando você passar o framework |
| `worldgen.sh` | ⏳ aguardando link | idem |
| `gamefactory.sh` | ⏳ aguardando link | idem |
| `blender_process.sh` | ✅ implementado | depende de Blender no PATH |

---

## Próximos passos

1. Você fornece os links dos frameworks restantes (TerraForge3D, WorldGen, GameFactory-3A, rsgeotools, 3DWorld).
2. Eu preencho os wrappers correspondentes com a CLI real.
3. Adiciono testes de integração em `tests/`.
