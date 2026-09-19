# Installation & Verified Setups

> Status real das ferramentas. Tudo que está marcado com ✅ foi baixado, instalado e **executado de verdade** em ambiente Debian 12 (bookworm) com 3 GB RAM, sem GPU.

**Data da verificação:** 2026-09-19
**Ambiente:** Debian 12, 3 GB RAM, sem GPU NVIDIA, sandbox cloud.

---

## ✅ Funciona end-to-end (verificado)

### Pipeline validado: `pipelines/verified_real.yaml`

```
Bycob/world (C++) → terrain.obj + texturas
        ↓
Blender 4.2.5 LTS (headless) → terrain.glb (3 LODs)
        ↓
gltf_validator (Python) → relatório JSON
        ↓
Godot 4.3 (carrega como PackedScene, 4 nós)
```

Para rodar:
```bash
python3 tools/python/pipeline_runner.py \
    --pipeline pipelines/verified_real.yaml \
    --var output_dir=./outputs/my_world/
```

---

## 📦 O que foi realmente instalado

### Dependências de sistema (apt)
```bash
apt install -y cmake build-essential git wget curl unzip pkg-config \
    libeigen3-dev libboost-all-dev libgl1-mesa-dev libglu1-mesa-dev \
    freeglut3-dev libglew-dev libpng-dev libtiff-dev zlib1g-dev \
    libjpeg-dev libopenal-dev libalut-dev libtirpc-dev libtirpc3 \
    openjdk-17-jdk-headless gdal-bin libgdal-dev libgeos-dev \
    libtiff-dev libgeotiff-dev libspatialindex-dev libsqlite3-dev \
    libboost-program-options-dev libboost-filesystem-dev libboost-system-dev \
    libboost-thread-dev libosmium2-dev libprotozero-dev libzip-dev \
    osmctools osmium-tool python3-yaml python3-pil python3-numpy \
    python3-opencv xz-utils
```

### Dependências Python (pip --break-system-packages, mirror Tsinghua)
```bash
pip install --break-system-packages --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    "numpy<2" "opencv-python<4.10" gltflib trimesh opensimplex pillow requests
```

### Ferramentas instaladas

| Ferramenta | Versão | Localização | Como verificar |
|------------|--------|-------------|----------------|
| **Blender** | 4.2.5 LTS | `/opt/tools/blender-4.2.5-linux-x64/blender` | `blender --version` |
| **Godot** | 4.3 stable | `/opt/tools/Godot_v4.3-stable_linux.x86_64` (symlink: `/usr/local/bin/godot`) | `godot --version` |
| **Bycob/world** | main (commit atual) | `/opt/tools/world/` (compilado em `build/`) | `ls /opt/tools/world/build/bin/` |
| **Java JDK** | 17.0.20 | `/usr/lib/jvm/java-17-openjdk-amd64` | `java -version` |
| **Terasology** | Omega (main) | `/opt/tools/Terasology/` (não compilado ainda) | `cd /opt/tools/Terasology && ls` |
| **Python deps** | pyyaml 6.0, gltflib ok, trimesh 5.1, opensimplex ok, PIL 12.2, numpy 1.26, cv2 4.9 | — | `python3 -c "import yaml, gltflib, trimesh, opensimplex, PIL, numpy, cv2"` |

---

## 🔧 Bycob/world — instalado e funcional

### Build
```bash
cd /opt/tools/world
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j2
```

### Binários gerados
```
build/bin/
├── libworld.so          ← biblioteca core
├── libpeace.so          ← wrapper Unity
├── libzlib.a
├── liblibpng.a
├── test_ini_files       ← testes de INI
├── test_terrain         ← gera terrain.obj + terrain.png
├── test_tree            ← gera modelos de árvores
├── test_reliefmap
├── mapper               ← gera mapa 2D de mundo (map.png 1024×1024)
└── mem_test
```

### Execução verificada
```bash
cd /opt/tools/world/build
./bin/test_terrain    # gera assets/terrain/terrain.obj + textures
./bin/test_tree       # gera assets/tree/*.obj + *.png
./bin/mapper          # gera map.png (1024×1024)
```

**Saídas reais geradas**:
- `terrain.obj` — 82,694 linhas, 32,768 vértices, 2.9 MB
- `terrain.png` — textura 129×129 grayscale
- `tree/instances.obj` + 30+ texturas PNG de árvores
- `map.png` — 1024×1024, mapa 2D top-down

### Limitação conhecida
- Vulkan e Irrlicht não estão disponíveis (skipped no cmake)
- 2 testes não compilam por causa de bug antigo do Catch (SIGSTKSZ) com glibc novo. A library principal compila e roda.

---

## 🎨 Blender — instalado e funcional

### Instalação
```bash
cd /opt/tools
curl -sL https://download.blender.org/release/Blender4.2/blender-4.2.5-linux-x64.tar.xz \
    -o blender.tar.xz
tar xf blender.tar.xz
ln -sf /opt/tools/blender-4.2.5-linux-x64/blender /usr/local/bin/blender
```

### Execução verificada
```bash
blender --background --python tools/python/asset_processor.py -- \
    --input terrain.obj --output terrain.glb --max-tris 50000 --lod-levels 3
```

**Saídas reais**:
- `terrain.glb` — 4.2 MB, glTF 2.0 binary, 3 LODs, 1 material, validado

### Bug corrigido durante verificação
O `asset_processor.py` estava quebrando porque Blender injeta `--background --python script.py --` em `sys.argv` sem strippar antes. Corrigido em `tools/python/asset_processor.py` com parser tolerante.

---

## 🎮 Godot 4.3 — instalado e funcional

### Instalação
```bash
cd /opt/tools
curl -sL https://github.com/godotengine/godot/releases/download/4.3-stable/Godot_v4.3-stable_linux.x86_64.zip \
    -o godot.zip
unzip godot.zip && rm godot.zip
ln -sf /opt/tools/Godot_v4.3-stable_linux.x86_64 /usr/local/bin/godot
```

### Execução verificada
```bash
cd /workspace/godot_test_project
godot --headless --script test_import.gd
```

**Saída**:
```
GLB existe: res://assets/terrain.glb (4272124 bytes)
Tipo do load: PackedScene
OK Carregou como PackedScene
OK Instanciou. Tipo raiz: Node3D
  Total de nos na cena: 4
```

Ou seja: o GLB gerado pelo Blender é carregado pelo Godot como `PackedScene` com 4 nós (Node3D raiz + 3 MeshInstance3D para os LODs).

---

## 📊 Pipeline executado: resultados reais

Arquivo: `outputs/verified_real/`

| Arquivo | Tamanho | Origem |
|---------|---------|--------|
| `bycob/terrain.obj` | 2.9 MB | Bycob C++ |
| `bycob/terrain.png` | 4 KB | Bycob C++ |
| `bycob/tree/*.png` (30+ arquivos) | ~70 MB | Bycob C++ |
| `final/terrain.glb` | 4.2 MB | Blender headless |
| `final/terrain.meta.json` | 1 KB | asset_processor.py |

**Relatório do pipeline**: `outputs/verified_real_pipeline_report.json`

---

## ❌ O que NÃO foi instalado (e por quê)

### Por falta de GPU (sem CUDA)
- **LichtFeld Studio** — treinamento de 3DGS é 100% CUDA. Install possível mas inutilizável.
- **WorldGen (ZiYang-xie)** — depende de PyTorch + CUDA. Install possível mas inutilizável.
- **GameFactory-3A** — depende de WorldGen.
- **COLMAP dense MVS** — tem modo CPU mas é **horrivelmente** lento (>10× que GPU). Install possível mas inviável.
- **TerraForge3D** — usa OpenCL; CPU mode é limitado.

### Por restrição de tempo/disco
- **rsgeotools** — a preparação do planet OSM demora **2-3 semanas** segundo o README. Não é falta de install, é falta de dados.
- **Meshroom** — requer AliceVision + Qt5 + Boost + CUDA para algumas etapas. Build de horas.
- **AliceVision CLI** — mesmo problema do Meshroom.
- **Terasology** — Java compila mas Gradle build de 30+ módulos é muito pesado (vários GB de cache). Repo clonado, ainda não buildado.
- **3DWorld** — dependências OpenGL legacy + Irrlicht; precisa investigar build script.
- **WebODM** — requer Docker, que pode ser instalado.

### Por restrição de tempo do build
- O **make de Bycob demorou ~5 min** para o subset que compilou. Builds maiores levariam horas.

---

## 🚀 O que você pode fazer AGORA

1. **Rodar o pipeline real**:
   ```bash
   cd /workspace/ai-3d-world-pipeline
   python3 tools/python/pipeline_runner.py \
       --pipeline pipelines/verified_real.yaml \
       --var output_dir=./outputs/my_world/
   ```

2. **Carregar no Godot**:
   ```bash
   mkdir meu_jogo && cd meu_jogo
   cp -r /workspace/godot_test_project/* .
   cp /workspace/ai-3d-world-pipeline/outputs/verified_real/final/terrain.glb assets/
   godot --headless --import
   godot --editor    # abre o editor
   ```

3. **Inspecionar assets Bycob**:
   ```bash
   ls /workspace/ai-3d-world-pipeline/outputs/verified_real/bycob/
   file /workspace/ai-3d-world-pipeline/outputs/verified_real/bycob/terrain.obj
   ```

---

## 📋 Próximas instalações recomendadas

Em ordem de prioridade e custo:

| Ferramenta | Custo de install | Pode funcionar sem GPU? |
|------------|------------------|--------------------------|
| Docker | 5 min | sim |
| WebODM (via Docker) | 30 min | sim (parcial) |
| Terasology (gradle build) | 30-60 min, ~5GB | sim |
| rsgeotools (binário) | 1 h + 2-3 semanas para planet OSM | sim |
| COLMAP (CPU mode) | 1-2 h compilação | sim (lento) |
| OpenDroneMap | via Docker | sim |
| 3DWorld | 30 min compilação | sim |
| Meshroom/AliceVision | 2-4 h compilação pesada | parcial |
| TerraForge3D | 1 h | parcial (CPU OpenCL) |
| LichtFeld | 1 h | NÃO (precisa CUDA) |
| WorldGen | 1 h + PyTorch+CUDA | NÃO (precisa CUDA) |
| GameFactory-3A | depende de WorldGen | NÃO |

Se quiser que eu continue instalando (Terasology, 3DWorld, COLMAP), é só pedir — mas cada um vai consumir 30min-2h desta sessão.
