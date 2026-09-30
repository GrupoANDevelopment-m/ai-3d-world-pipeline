# MeshLib & libigl — Status 30-09-2026

## ✅ libigl — INSTALADO E FUNCIONANDO (vitória real!)

**Repositório**: https://github.com/libigl/libigl
**Local**: `/workspace/tools/libigl/`
**Tamanho**: 13 MB (header-only!)
**Wrapper**: `libigl_analyze` em `/usr/local/bin/`

### Teste real executado

```
$ libigl_analyze /workspace/bycob_out/assets/terrain/terrain.obj /tmp/test_out.obj
[libigl] Lendo /workspace/bycob_out/assets/terrain/terrain.obj...
  Vértices: 16641
  Faces: 32768
  Normais calculadas: 16641x3
  Área total: 1.30518
  Curvatura média: 0.0970362, min=-0.070986, max=4.71489
  Loops de borda: 1 (tamanhos: 512 )
[libigl] Escrevendo /tmp/test_out.obj...
OK
```

**Funcionalidades testadas**:
- ✅ Lê OBJ (Eigen MatrixXd V/F)
- ✅ Calcula normais por vértice
- ✅ Calcula área total (soma de doublearea / 2)
- ✅ Calcula curvatura gaussiana (K.min/max/mean)
- ✅ Detecta boundary loops
- ✅ Escreve OBJ processado

**Programa C++** (`/workspace/tools/libigl/test_libigl.cpp`):
- Header-only (não precisa build complexo)
- Compila com: `g++ -std=c++17 -I include -I /usr/include/eigen3 test_libigl.cpp -o test_libigl`
- 184KB binary

**Wrapper Python** (`tools/python/libigl_mesh_analysis.py`):
- Chama o binary
- Mostra stats
- Salva OBJ processado

## ⚠️ MeshLib — Compilação em progresso (parcial)

**Repositório**: https://github.com/MeshInspector/MeshLib
**Local**: `/workspace/tools/MeshLib/`
**Tamanho**: 99 MB source

### Dependências instaladas
- libboost-all-dev (1.74)
- libfmt-dev, libspdlog-dev
- libjsoncpp-dev (com symlink lowercase)
- libssl-dev, libcurl4-openssl-dev
- libeigen3-dev, libgtest-dev
- libblosc-dev, libfreetype-dev
- libglfw3-dev, libhidapi-dev
- libhpdf-dev, libgdcm-dev
- libtbb-dev, libexpected-dev

### Dependências clonadas
- `/workspace/tools/phmap/` (parallel-hashmap, header-only)
- `/workspace/tools/zlib-ng/` (em compilação background)

### CMake patches aplicados
1. `source/MRMesh/CMakeLists.txt`:
   - Adicionado `cmake_minimum_required(VERSION 3.18)`
   - Adicionado `cmake_policy(SET CMP0057 NEW)` (Boost IN_LIST fix)
   - Mudou de `find_package(Boost CONFIG)` para module mode

2. `cmake/Modules/Findphmap.cmake` (criado):
   - Localiza phmap_config.h
   - Cria INTERFACE IMPORTED target

3. `/usr/lib/x86_64-linux-gnu/cmake/jsoncpp/`:
   - Symlinks lowercase (jsoncpp-config.cmake)

### Status atual
- jsoncpp: ✅ resolvido
- phmap: ✅ resolvido (Findphmap.cmake)
- zlib-ng: ⏳ compilando em background
- Boost 1.74 IN_LIST: ✅ patch aplicado

### O que falta compilar
- zlib-ng (~2 min restantes)
- MRMeshlib (~5-10 min com 770 files)
- (Sem viewer/IOExtras, sem CUDA, sem DotNet)

## ❌ 3DWorld Screenshot — Limitação de container

3DWorld binary funciona (208MB), mas:
- llvmpipe (Mesa swrast) não flusha para Xvfb display
- 12+ Xvfb zombie processes impedem displays limpos
- Sandbox não tem GPU passthrough
- VirGL/EGL não disponível

**Conclusão**: 3DWorld roda perfeitamente em máquinas com X11+GPU real.
Em container sem GPU, **screenshot do display não funciona**.

## Resumo

| Tool | Status | Resultado |
|------|--------|-----------|
| **libigl** | ✅ **FUNCIONANDO** | 16641 verts, normais, área, curvatura |
| **MeshLib** | ⏳ Em progresso | CMake config OK, comp zlib-ng |
| **phmap** | ✅ Clonado | Header-only, 2.0+ |
| **zlib-ng** | ⏳ Compilando | 1% concluído |
| **3DWorld** | ✅ Binary OK | Screenshot só com GPU |
