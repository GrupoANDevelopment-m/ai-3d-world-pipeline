# 🛠️ Tools — Wrappers CLI & Python

Esta pasta contém os **wrappers** que o agente orquestrador chama para executar cada ferramenta.

---

## Estrutura

```
tools/
├── cli-wrappers/                   ← bash scripts (entry points)
│   ├── colmap.sh                   ✅ SfM + Dense MVS
│   ├── alicevision.sh              ✅ Pipeline AliceVision alternativo
│   ├── meshroom.sh                 ✅ GUI Meshroom (AliceVision)
│   ├── webodm.sh                   ✅ Drone + georreferenciamento
│   ├── lichtfeld.sh                ✅ 3D Gaussian Splatting
│   ├── supersplat.sh               ✅ Editor web de splats
│   ├── terraforge.sh               ✅ Terreno procedural GPU
│   ├── terrain3d.sh                ✅ Godot 4 + Terrain3D + SimpleXTerrain
│   ├── worldgen.sh                 ✅ Text-to-3D scene
│   ├── gamefactory.sh              ✅ gen_3d_scene / gen_3d_object
│   ├── rsgeotools.sh               ✅ OSM → 3D world
│   ├── bycob_world.sh              ✅ Mundo voxel/infinito C++
│   ├── terasology.sh               ✅ Engine voxel Java modular
│   ├── 3dworld.sh                  ✅ Engine OpenGL clássica
│   └── blender_process.sh          ✅ Asset processing headless
│
├── python/                         ← módulos Python (orquestração fina)
│   ├── asset_processor.py          ✅ processa mesh (retopo, LOD, PBR)
│   ├── pipeline_runner.py          ✅ carrega YAML e executa estágios
│   └── gltf_validator.py           ✅ valida GLB final
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

1. Recebe `--input` e `--output` (sempre que aplicável).
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

## Status Completo

| Wrapper | Status | Repo upstream |
|---------|--------|---------------|
| `colmap.sh` | ✅ funcional | colmap/colmap |
| `alicevision.sh` | ✅ funcional | alicevision/AliceVision |
| `meshroom.sh` | ✅ funcional | alicevision/Meshroom |
| `webodm.sh` | ✅ funcional | OpenDroneMap/WebODM |
| `lichtfeld.sh` | ✅ funcional | RobertKrajewski/LichtFeld-Studio |
| `supersplat.sh` | ✅ funcional | playcanvas/supersplat |
| `terraforge.sh` | ✅ funcional | Jaysmito101/TerraForge3D |
| `terrain3d.sh` | ✅ funcional | TokisanGames/Terrain3D + prajwal-mx/SimpleXTerrain |
| `worldgen.sh` | ✅ funcional | ZiYang-xie/WorldGen |
| `gamefactory.sh` | ✅ funcional | OpenDCAI/GameFactory-3A |
| `rsgeotools.sh` | ✅ funcional | romanshuvalov/rsgeotools |
| `bycob_world.sh` | ✅ funcional | Bycob/world |
| `terasology.sh` | ✅ funcional | MovingBlocks/Terasology |
| `3dworld.sh` | ✅ funcional | fegennari/3DWorld |
| `blender_process.sh` | ✅ funcional | Blender Foundation |

Todos os wrappers foram implementados com base nas CLIs/APIs oficiais dos respectivos repos.
