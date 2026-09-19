---
name: voxel-world
version: 0.1.0
triggers:
  - "mundo voxel"
  - "minecraft like"
  - "mundos ilimitados"
  - "world infinite"
  - "world streaming"
inputs:
  required:
    - engine: bycob_world | terasology
  optional:
    - terrain: bool
    - vegetation: bool
    - cities: bool
    - voxels: bool
    - seed: int
    - modules: string   # CSV para Terasology
    - timeout_s: int    # tempo de captura
outputs:
  type: world | voxels
  format: bin | modmap | json
calls:
  - tool: bycob_world
    method: cpp
  - tool: terasology
    method: gradle
fallbacks:
  - if: bycob_unavailable
    then: terasology
  - if: terasology_unavailable
    then: bycob
---

# 🧊 Skill: Voxel / Infinite World

Gera mundos massivos voxel-style com Bycob/world ou Terasology.

---

## Opções

### A — Bycob/world (C++)

> Repo: https://github.com/Bycob/world

Engine C++ leve para mundos infinitos.

```bash
bash tools/cli-wrappers/bycob_world.sh \
    --output ./world \
    --terrain \
    --vegetation \
    --cities \
    --voxels \
    --seed 42
```

**Características**:
- Terrenos, vegetação, cidades, LOD automático
- Streaming em tempo real (exploração ilimitada)
- Vulkan renderer opcional (`VkWorld`)
- Irrlicht 3D viewer opcional (`World3D`)
- Paz demo: visualizador leve sem dependências

**Projetos derivados**:
- `World` — biblioteca core (sem deps)
- `VkWorld` — renderer Vulkan
- `World3D` — viewer Irrlicht
- `Peace` — demo leve

---

### B — Terasology (Java/Gradle)

> Repo: https://github.com/MovingBlocks/Terasology

Engine voxel open source modular (estilo Minecraft + arquiteturas complexas).

```bash
bash tools/cli-wrappers/terasology.sh \
    --output ./terasology_out \
    --seed 42 \
    --modules CoreWorlds,CoreAssets,City \
    --timeout 600
```

**Módulos úteis**:
- `CoreWorlds` — geração básica de mundos
- `CoreAssets` — assets base
- `City` — prédios, ruas, infraestrutura
- `Sample` — exemplos de mecânicas
- `Adventure` — cenários prontos

**Launcher oficial**: https://terasology.org/downloads/

**Build local** (requer JDK 17):
```bash
git clone https://github.com/MovingBlocks/Terasology
cd Terasology
./gradlew run -Pheadless=true -Pseed=42
```

---

## Quando usar cada um

| Caso | Recomendação |
|------|--------------|
| Mundos voxel para jogos | Terasology (Java, modular) |
| Streaming massivo C++ | Bycob/world |
| Mobile/embedded | Bycob/world (Peace demo) |
| Cidades procedurais | Bycob/world --cities |
| Educational / city-building | Terasology + módulo City |
| Pesquisa voxel | Terasology (multi-repo workspace) |

---

## Saída

```json
{
  "engine": "bycob_world",
  "seed": 42,
  "features": ["terrain", "vegetation", "cities", "voxels"],
  "output": "./world/",
  "captured_for_s": 600
}
```
