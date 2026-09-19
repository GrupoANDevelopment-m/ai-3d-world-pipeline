---
name: worldgen
version: 0.2.0
triggers:
  - "text to 3d"
  - "text to world"
  - "gerar mundo de prompt"
  - "world generation"
  - "scene from text"
  - "gaussian splat from text"
inputs:
  required:
    - prompt: string
  optional:
    - reference_image: string
    - return_mesh: bool
    - use_sharp: bool
    - low_vram: bool
outputs:
  type: scene
  format: ply  # gaussian splat ou mesh
calls:
  - tool: worldgen
    method: python
  - tool: lichtfeld
    method: cli
  - tool: gamefactory
    method: python
fallbacks:
  - if: worldgen_unavailable
    then: lichtfeld+gamefactory
  - if: low_vram
    then: enable_low_vram_mode
---

# 🪄 Skill: WorldGen (text-to-3D)

Gera cena 3D (Gaussian Splat ou mesh) a partir de prompt em linguagem natural.

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
[WorldGen ZiYang-xie/WorldGen]
   ├── text-to-scene (.ply Gaussian Splat)
   └── image-to-scene
        │
        ▼
[Opcional: return_mesh=True → mesh via Open3D]
        │
        ▼
[Asset processing] (Blender ou direct)
        │
        ▼
[Cena montada em GLB/splat]
```

---

## Uso Real (ZiYang-xie/WorldGen)

### Instalação

```bash
git clone --recursive https://github.com/ZiYang-xie/WorldGen.git
cd WorldGen
conda create -n worldgen python=3.11
conda activate worldgen
pip3 install torch torchvision
pip install .
pip install git+https://github.com/EnVision-Research/DA-2.git#subdirectory=src --no-deps
pip install git+https://github.com/facebookresearch/pytorch3d.git --no-build-isolation
# Aceite a licença FLUX.1-dev em https://huggingface.co/black-forest-labs/FLUX.1-dev
huggingface-cli login
```

### Modos

```python
from worldgen import WorldGen
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Modo t2s (text-to-scene)
wg = WorldGen(mode="t2s", device=device, low_vram=False)
splat = wg.generate_world("A beautiful landscape with a river and mountains")
splat.save("scene.ply")

# Modo i2s (image-to-scene)
wg = WorldGen(mode="i2s", device=device)
scene = wg.generate_world(image=pil_img, prompt="Optional: refine prompt")

# Modo mesh
mesh = wg.generate_world("cozy bedroom", return_mesh=True)
o3d.io.write_triangle_mesh("bedroom.ply", mesh)
```

### Wrapper CLI

```bash
# Já implementado em tools/cli-wrappers/worldgen.sh
bash tools/cli-wrappers/worldgen.sh \
    --prompt "Vila costeira portuguesa com falésias" \
    --output ./scene.ply
```

---

## Comparação de modelos text-to-3D

| Modelo | Velocidade | Qualidade | Output | Open Source |
|--------|-----------|-----------|--------|-------------|
| **WorldGen (ZiYang-xie)** | 2-5 min | alta | Gaussian Splat (.ply) | ✅ |
| GameFactory-3A gen_3d_scene | 5-10 min | boa | GLB/OBJ (engine adapters) | ✅ |
| Meshy | rápido | média | GLB | ❌ (API paga) |
| TripoSR | muito rápido | média | GLB | ✅ |
| LRM (Large Rec. Model) | lento | alta | GLB | ✅ |

---

## Validação

```bash
python tools/python/gltf_validator.py --input scene.ply
# ou
python tools/python/pipeline_runner.py --pipeline pipelines/procedural.yaml --dry-run
```

---

## Saída

```json
{
  "scene": "./output/coastal/scene.ply",
  "mode": "t2s",
  "prompt": "Vila costeira portuguesa com falésias e farol ao entardecer",
  "use_sharp": false,
  "polycount_or_splat_count": 1_847_000
}
```
