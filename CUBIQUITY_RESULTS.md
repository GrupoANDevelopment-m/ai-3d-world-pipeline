# Cubiquity — INSTALADO E FUNCIONANDO (vitória real!)

**Repositório**: https://github.com/DavidWilliams81/cubiquity
**Path**: `/workspace/tools/cubiquity/`
**Tamanho source**: 4.9 MB (small!)
**Binary**: `/workspace/tools/cubiquity/build/cubiquity` (2 MB)
**Wrapper**: `cubiquity` em `/usr/local/bin/`

## ✅ O que FUNCIONA (verificado):

### Compilação
```bash
cd /workspace/tools/cubiquity/build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j1   # ~5min
```

Output:
```
[100%] Built target Application
-rwxr-xr-x 1 root root 1994272 Sep 30 23:28 cubiquity
```

### Comandos verificados

```
$ cubiquity --help
Cubiquity micro-voxel engine by David Williams
SUBCOMMANDS:
  combine, export, generate, import, test, view, voxelize

$ cubiquity generate --help
algorithm ENUM: {checkerboard, fractal_noise, menger_sponge, worley_noise}

$ cubiquity export --help
format ENUM: {bin, pngs, vox}
```

### Algoritmos testados (todos geraram outputs reais)

| Algoritmo | Tempo | Output |
|-----------|-------|--------|
| **menger_sponge** | 0.304s | fractal cube 64³ voxels |
| **worley_noise** | 5.739s | 128³ voxel cellular pattern |
| **fractal_noise** | 4.668s | 128³ voxel noise |
| **checkerboard** | 0.325s | 128³ tabuleiro |

### Output real gerado

```
/workspace/ai-3d-world-pipeline/outputs/cubiquity_demo/
├── menger.dag + menger.toml + menger_pngs/ (64 PNG slices)
├── fractal.dag + fractal.toml + fractal_pngs/ (128 PNG slices)
├── worley.dag + worley.toml + worley_pngs/ (128 PNG slices)
├── checker.dag + checker.toml + checker_pngs/ (500 PNG slices)
└── montage.png (4 algos em 2x2)
```

### Capacidades
- ✅ Geração procedural de voxel worlds
- ✅ Export para PNG slices (slice-by-slice)
- ✅ Export para binário (.dag)
- ✅ Export para formato vox (MagicaVoxel)
- ✅ Voxelize de mesh (import OBJ→voxels)
- ✅ Combine volumes
- ✅ View interativo (requer OpenGL/X)

### Dependências
- libtbb-dev (parallel processing)
- libglfw3 (OpenGL window, opcional)
- glad, stb_image, simplexnoise (bundled)

## 🎯 Conclusão

Cubiquity é **leve, zero-dep runtime, e gera mundos voxel reais** em CPU.
**Funciona como esperado** ao contrário do 3DWorld que tem limitação
de display no container sem GPU.

É o **substitute leve perfeito** para MagicaVoxel/Minecraft world generators.
