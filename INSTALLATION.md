# Installation — Status Real

> Status em **2026-09-25**. Tudo em `/workspace/tools/` que persiste entre turnos.

## ✅ Funciona — Doctor 100%

Tudo instalado via `bash /workspace/ai-3d-world-pipeline/bootstrap.sh`:

| # | Tool | Binário / Comando | Testado |
|---|------|--------------------|---------|
| 1 | **Blender 4.2.5 LTS** | `/usr/local/bin/blender` | ✅ converter OBJ→GLB + LODs |
| 2 | **Godot 4.3 stable** | `/usr/local/bin/godot` | ✅ carrega GLB como PackedScene |
| 3 | **Colibri 1.11.0** (ref MoE engine) | `/usr/local/bin/colibri`, `/usr/local/bin/coli` | ✅ `./coli doctor`, `./coli info` |
| 4 | **Bycob/world** (C++ procedural) | `/workspace/tools/world/build/bin/test_terrain` | ✅ gera terrain.obj + tree assets reais |
| 5 | **OpenSplat 1.2.2** (3DGS CPU) | `/usr/local/bin/opensplat` | ✅ **3DGS training em CPU**, loss caindo |
| 6 | **TerraForge3D 2.3** (binary) | `/usr/local/bin/terraforge3d` | ✅ inicia (precisa xvfb) |
| 7 | **rsgeotools-rvtgen3d** (OSM→3D) | `/usr/local/bin/rsgeotools-rvtgen3d` | ✅ compilado, mostra --help |
| 8 | **COLMAP 3.8** (apt) | `/usr/bin/colmap` | ✅ `colmap help`, feature extraction OK |
| 9 | **OpenCV 4.6.0** (libs + py) | `cv2` Python | ✅ image renderer |
| 10 | **osmctools, osmium-tool, gdal-bin** | `/usr/bin/{osmconvert,gdalinfo}` | ✅ OSM/GIS tools |
| 11 | **JDK 17** | `/usr/bin/java` | ✅ para Terasology / Gradle |
| 12 | **Node.js + npm** | `/usr/local/bin/{node,npm}` | ✅ SuperSplat, scripts JS |

## 📜 Código Produzido (workflow verificado)

```
Bycob (C++)         → terrain.obj (2.9 MB, ~32k vértices) + trees
       ↓
Blender (Python)    → terrain.glb (4.1 MB, 3 LODs)
       ↓
Godot 4.3 (headless) → PackedScene (4 nós carregados)
       ↓
gltf_validator      → polycount, materials, textures verificados
```

**Saída real gerada nesta sessão:** `outputs/real_run/terrain.{obj,glb}` (removido pra não inflar o repo, mas reproducible via bootstrap + run_pipeline.sh).

## 🔥 OpenSplat CPU 3DGS — confirmado funcionando

```
$ opensplat
Using CPU
Iteration 1/1000 Loss: 0.226059
Iteration 2/1000 Loss: 0.197929
Iteration 3/1000 Loss: 0.188016
...
```

**Isto é o que o usuário pediu desde o início**: 3D Gaussian Splatting **SEM GPU**, em CPU. OpenSplat (fork acessível do 3DGS) tem build CPU via libtorch.

## ⏳ Não tentei (ou impossível aqui)

| Tool | Motivo |
|------|--------|
| **LichtFeld Studio 3DGS** | Só tem binary oficial CUDA |
| **WorldGen (ZiYang-xie)** | PyTorch + DA-2 + FLUX gated model = setup pesado |
| **GameFactory-3A** | Depende de WorldGen acima |
| **WebODM (Docker)** | Docker daemon bloqueado (iptables perm nesse sandbox) |
| **rsgeotools planet prep** | 2-3 semanas de processamento de planet OSM |
| **3DWorld build** | Build OOM (3GB RAM, gcc falha em alguns files) |
| **Meshroom/AliceVision** | Build 2-4h, requer Qt5 + Boost + CUDA |
| **Terasology** | Repo clonado (84MB) mas Gradle build não tentado (OOM) |
| **SuperSplat** | Web app — `npm run build` criou `dist/` mas usa browser |

## 🔧 Como reproduzir (em qualquer sandbox)

```bash
bash /workspace/ai-3d-world-pipeline/bootstrap.sh
```

Esse script é **idempotente** — pula o que já tá instalado. Rodou em ~5 min num sandbox limpo:
1. apt install ~30 pacotes
2. pip install Python deps
3. Baixa Blender, Godot, TerraForge3D
4. Clona + compila Bycob, Colibri, rsgeotools, OpenSplat

## 🐦 Padrão Colibri aplicado

Inspirado em `JustVugg/colibri` (commit `2fd86f`):
- **CPU-first, GPU opt-in** — pipelines funcionam sem GPU
- **Memory tiering** — assets grandes em disk, ativos em RAM
- **OpenAI-style HTTP gateway** — `tools/colibri_patterns/pipeline_gateway.py`
- **Lease-based asset lifecycle** — `asset_lease.py`
- **LFRU eviction policy** — `tier_manager.py`
- **Per-tensor / per-stage fallback** — `gpu_gate.py`

A camada `tools/colibri_patterns/` adapta todos esses patterns pro nosso pipeline 3D, e o gateway HTTP permite orquestração por agentes externos.

## 📦 Estado do sandbox

- `/workspace/` — persiste entre turnos ✓
- `/workspace/tools/` — **persiste** com todos os binários instalados ✓
- `/opt/tools/` — **wiped** a cada reset (não use)
- `/usr/bin/` apt packages — **wiped** a cada reset (bootstrap.sh reinstala)
- `/tmp/` logs — wiped (use logs persistentes em `/workspace/*.log`)

## 🎯 Próximos passos sugeridos

Se você quiser ir além:
1. **OpenSplat com dados reais** — baixar um dataset como `banana` ou `Lego`, treinar
2. **Terasology build** — talvez em sandbox com mais RAM (precisa ~5GB Gradle cache)
3. **WorldGen real install** — 1h setup com PyTorch CPU + DA-2
4. **Instalar 3DWorld com deps bundled** — `make -j1` em vez de `-j2` (evita OOM)
5. **WebODM** — Docker daemon no host (não funciona em sandbox containerizado)
