# Exemplo: Prompt → Mundo 3D

> Caso de uso: gerar "Vila costeira portuguesa com falésias e farol ao entardecer" para um jogo indie.

---

## Input

```yaml
prompt: "Vila costeira portuguesa com falésias e farol ao entardecer"
biome: coastal
size_km: 4
style: realistic
```

## Comando

```bash
python tools/python/pipeline_runner.py \
    --pipeline pipelines/procedural.yaml \
    --var prompt="Vila costeira portuguesa com falésias e farol ao entardecer" \
    --var biome=coastal \
    --var size_km=4
```

## O que acontece

1. **WorldGen** lê o prompt, gera cena base (skybox, lighting de entardecer, geometria de falésia).
2. **TerraForge3D** gera heightmap costeiro de 4×4 km com erosão + rios.
3. **GameFactory-3A** espalha casas brancas mediterrâneas, farol, vegetação rasteira.
4. **Blender** processa (retopologia, LODs, PBR atlas).
5. **Godot** monta a cena final.

## Saídas

```
outputs/coastal_village/
├── base_scene/scene.glb
├── terrain/
│   ├── heightmap.png (16-bit, 2048×2048)
│   ├── splat.png (PBR layers)
│   └── terrain.glb
├── vegetation/
│   ├── house_branca_01.glb
│   ├── farol.glb
│   └── ...
├── final/scene.glb
└── report.json
```

## Tempo estimado (RTX 3080)

| Etapa | Tempo |
|-------|-------|
| WorldGen cena base | ~3 min |
| TerraForge heightmap + erosion | ~2 min |
| GameFactory scattering | ~5 min |
| Blender processing | ~5 min |
| **Total** | **~15 min** |

## Iteração

Para ajustar o resultado sem rerodar tudo:

```bash
# Trocar apenas a vegetação
python tools/python/pipeline_runner.py \
    --pipeline pipelines/procedural.yaml \
    --var prompt="Vila costeira portuguesa com falésias e farol ao entardecer" \
    --skip-stage worldgen_base,terrain_procedural
```

(O `--skip-stage` será implementado na próxima versão.)

## Customização do Estilo

```yaml
# Editar pipelines/procedural.yaml
stages:
  - id: worldgen_base
    tool: worldgen
    params:
      prompt: "{{prompt}}"
      style: stylized   # ← troque para stylized / anime / lowpoly
      time_of_day: dusk
      weather: clear
```
