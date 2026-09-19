# 🐦 Colibri Patterns — Adaptado do JustVugg/colibri

> Adaptação dos patterns arquiteturais do Colibri (https://github.com/JustVugg/colibri)
> para o pipeline de geração de mundos 3D.

## O que o Colibri faz (e o que NÃO faz)

**O que ele faz:**
- Roda modelos MoE massivos (GLM-5.2, 744B params) em hardware comum **sem GPU**
- Faz isso via **memory tiering** (storage → RAM → VRAM opcional) + **expert streaming**
- CPU-first, GPU-opt-in (mesma engine serve ambos)
- Per-tensor fallback: se GPU falha num tensor, recomputa em CPU sem crash

**O que ele NÃO faz:**
- Não é um emulador de GPU. Não transforma uma RTX 4090 numa RTX 5090.
- Não acelera CUDA → CPU. Matrix multiplies ainda rodam no hardware que estiver lá.
- Não roda QUALQUER modelo. Foi escrito especificamente para MoE LMs.

## O que isso SIGNIFICA pro nosso pipeline

**Os patterns do Colibri são adaptáveis**, mas com honestidade:

| Pattern do Colibri | Adapta direto pro pipeline? | Limitação |
|--------------------|------------------------------|-----------|
| Memory tiering (storage/RAM/VRAM) | ✅ Sim | Para assets 3D grandes (splats, point clouds) |
| CPU-first, GPU opt-in | ✅ Sim | Cada wrapper detecta GPU no runtime |
| Per-tensor fallback | ⚠️ Parcial | COLMAP/LichtFeld não têm CPU-GPU mixed execution real |
| Asset streaming | ✅ Sim | Splats de 1-2GB viram resident + streaming |
| OpenAI-style API gateway | ✅ Sim | Single endpoint HTTP pra orquestrar o pipeline |
| Lease-based asset lifecycle | ✅ Sim | Explicit `lookup()/release()` para cada asset |
| Heat-based LRU/LFRU | ✅ Sim | Cache dos splats/heightmaps mais usados |

**O que NÃO dá pra fazer**: rodar 3DGS training do LichtFeld em CPU. Ou treinamento PyTorch do WorldGen em CPU. Esses tools fazem matrix multiplies maciças que CPU não aguenta em tempo hábil.

**O que DÁ pra fazer**: deixar o pipeline **funcionar** sem GPU usando alternativas CPU-only (Bycob → terreno, OpenSimplex → heightmap, Blender → processamento, Godot → render), e quando GPU existe, **aproveitar automaticamente** para os tools que têm CPU+GPU modes (COLMAP, etc.).

## Componentes

| Arquivo | Função | Pattern Colibri |
|---------|--------|-----------------|
| `gpu_probe.py` | Detecta GPU e define flag `COLI_GPU=0/1` | `COLI_CUDA=1` env var |
| `tier_manager.py` | Decide o que fica em RAM vs stream de disk | `expert_store` + `tier_pick_lfru` |
| `asset_lease.py` | Lifecycle explícito lookup/release de assets | `ColiExpertStore` + `ColiExpertView` |
| `asset_streamer.py` | Stream de splats/heightmaps grandes sem carregar tudo | `expert_host_ensure` + `pread` + `mmap` |
| `pipeline_gateway.py` | API HTTP OpenAI-style pra orquestrar tudo | `coli serve` + `coli web` |
| `cli.py` | Entry point unificado `pipeline ...` | `./coli` |

## Uso

```bash
# Detecta GPU
python3 -m tools.colibri_patterns.gpu_probe

# Tier manager
python3 -c "
from tools.colibri_patterns.tier_manager import TierManager
m = TierManager(ram_budget_mb=2048, disk_path='/tmp/assets')
print(m.plan({'scene.ply': 500_000_000, 'small.glb': 5_000_000}))
"

# API gateway
python3 -m tools.colibri_patterns.cli serve --port 8765
# Em outro terminal:
curl -X POST http://localhost:8765/v1/pipeline/run \
    -H 'Content-Type: application/json' \
    -d '{"pipeline": "verified_real", "outputs_dir": "./outputs/x/"}'
```

## Honesto sobre limitações

Se você veio aqui esperando "rodar LichtFeld 3DGS training sem GPU" — não vai rolar.
Se você veio esperando "rodar COLMAP dense MVS sem GPU em tempo razoável" — também não.

O que VAI rodar sem GPU (com esta camada):
- ✅ Bycob/world (já verificado)
- ✅ OpenSimplex / noise-based heightmaps (Python)
- ✅ Blender asset processing
- ✅ Godot rendering básico (GL Compatibility)
- ✅ rsgeotools (sem preparo de planet)
- ✅ Terasology / Bycob (voxel)

O que SÓ funciona com GPU (e fica desabilitado se `COLI_GPU=0`):
- ❌ LichtFeld 3DGS training
- ❌ WorldGen text-to-3D (ZiYang-xie)
- ❌ GameFactory-3A (depende de WorldGen)
- ❌ TerraForge3D GPU mode
- ❌ COLMAP dense MVS (CPU existe mas inviável)

A camada `colibri_patterns` documenta isso explicitamente e dá fallback para cada caso.
