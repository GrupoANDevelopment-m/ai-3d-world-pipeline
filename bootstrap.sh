#!/usr/bin/env bash
# =============================================================================
# bootstrap.sh — Setup completo (idempotente, persistente em /workspace/tools/)
# =============================================================================
# Instala tudo de uma vez:
#   - apt packages (resilientes — reinstalla se sandbox resetar)
#   - PyTorch CPU + libtorch
#   - Repos clonados em /workspace/tools/ (persiste entre turnos)
#   - Builds C++ (Bycob, OpenSplat, rsgeotools)
#   - Downloads binários (Blender, Godot, TerraForge3D)
#
# Tudo persistido em /workspace/tools/ pra sobreviver reset do sandbox.
# Rode: bash /workspace/ai-3d-world-pipeline/bootstrap.sh
# =============================================================================
set -e

WORKSPACE=/workspace
TOOLS="$WORKSPACE/tools"
PIPELINE="$WORKSPACE/ai-3d-world-pipeline"
LOG="$WORKSPACE/bootstrap_$(date +%s).log"

mkdir -p "$TOOLS"
exec > >(tee -a "$LOG") 2>&1
echo "=== AI 3D World Pipeline bootstrap @ $(date) ==="

# ---------- Apt ----------
echo ""
echo "[1/9] apt packages..."
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    cmake build-essential git wget curl unzip pkg-config \
    libglew-dev libopencv-imgcodecs406 libopencv-imgproc406 \
    libopencv-core406 libopencv-calib3d406 libopencv-features2d406 \
    libopencv-highgui406 libopencv-flann406 libopencv-contrib406 \
    libgdal-dev libpng-dev libtiff-dev libopenal-dev libalut-dev libglm-dev \
    libboost-all-dev libeigen3-dev libtirpc-dev libsqlite3-dev libjsoncpp-dev \
    libosmium-dev libgeos-dev libboost-program-options-dev \
    libboost-filesystem-dev libboost-system-dev libboost-thread-dev \
    libzip-dev libcurl4-openssl-dev libxmu-dev libxi-dev libxrender-dev libzstd-dev \
    xvfb mesa-utils libgl1-mesa-dri \
    openjdk-17-jdk-headless sqlite3 ca-certificates curl gnupg \
    colmap osmctools osmium-tool gdal-bin nodejs npm 2>&1 | tail -3
echo "  ✓ apt done"

# ---------- Python ----------
echo ""
echo "[2/9] Python deps..."
pip install --break-system-packages --index-url https://pypi.tuna.tsinghua.edu.cn/simple --quiet \
    pyyaml gltflib trimesh opensimplex pillow numpy requests scipy \
    opencv-python-headless plyfile warp-lang 2>&1 | tail -3
echo "  ✓ python done"

# ---------- Blender ----------
echo ""
echo "[3/9] Blender 4.2.5 LTS..."
if [[ ! -x "$TOOLS/blender-4.2.5-linux-x64/blender" ]]; then
    cd "$TOOLS"
    curl -sL "https://download.blender.org/release/Blender4.2/blender-4.2.5-linux-x64.tar.xz" -o blender.tar.xz
    tar xf blender.tar.xz && rm blender.tar.xz
fi
echo "  ✓ Blender $(basename $TOOLS/blender-*)"

# ---------- Godot ----------
echo ""
echo "[4/9] Godot 4.3..."
if [[ ! -x "$TOOLS/Godot_v4.3-stable_linux.x86_64" ]]; then
    cd "$TOOLS"
    curl -sL "https://github.com/godotengine/godot/releases/download/4.3-stable/Godot_v4.3-stable_linux.x86_64.zip" -o godot.zip
    unzip -q godot.zip && rm godot.zip
fi
echo "  ✓ Godot 4.3"

# ---------- TerraForge3D ----------
echo ""
echo "[5/9] TerraForge3D..."
if [[ ! -f "$TOOLS/TerraForge3D" ]]; then
    cd "$TOOLS"
    curl -sL "https://github.com/Jaysmito101/TerraForge3D/releases/download/v2.3/TerraForge3D.Linux.tar.gz" -o tf3d.tar.gz
    tar xf tf3d.tar.gz && rm tf3d.tar.gz
fi
echo "  ✓ TerraForge3D ($(file $TOOLS/TerraForge3D | cut -d: -f2-))"

# ---------- Colibri ----------
echo ""
echo "[6/9] Colibri (reference MoE engine, CPU build)..."
if [[ ! -x "$TOOLS/colibri/c/colibri" ]]; then
    cd "$TOOLS"
    GIT_SSL_NO_VERIFY=true git -c http.sslVerify=false clone --depth 1 https://github.com/JustVugg/colibri.git
    cd colibri/c && ./setup.sh 2>&1 | tail -3
fi
echo "  ✓ Colibri"

# ---------- Bycob/world ----------
echo ""
echo "[7/9] Bycob/world (C++ procedural world)..."
if [[ ! -x "$TOOLS/world/build/bin/test_terrain" ]]; then
    cd "$TOOLS"
    GIT_SSL_NO_VERIFY=true git -c http.sslVerify=false clone --depth 1 https://github.com/Bycob/world.git
    cd world && mkdir -p build && cd build
    cmake .. 2>&1 | tail -3
    make -j2 2>&1 | tail -3 || true
fi
echo "  ✓ Bycob (C++)"

# ---------- rsgeotools ----------
echo ""
echo "[8/9] rsgeotools (OSM→3D)..."
if [[ ! -x "$TOOLS/rsgeotools/bin/rsgeotools-rvtgen3d" ]]; then
    cd "$TOOLS"
    apt install -y -qq libgeos-dev libsqlite3-dev libjsoncpp-dev libzip-dev libcurl4-openssl-dev libtiff-dev libboost-program-options-dev libboost-filesystem-dev libboost-system-dev libboost-thread-dev 2>&1 | tail -2
    GIT_SSL_NO_VERIFY=true git -c http.sslVerify=false clone --depth 1 https://github.com/romanshuvalov/rsgeotools.git
    cd rsgeotools
    # Patch Makefile: -lgeos_c no final do link + -lstdc++
    sed -i 's/$(SRC_DIR)\/csv2rvtdata\/csv.c $(SRC_DIR)\/csv2rvtdata\/csv2rvtdata.cpp/$(SRC_DIR)\/csv2rvtdata\/csv.c $(SRC_DIR)\/csv2rvtdata\/csv2rvtdata.cpp -lgeos_c -lstdc++/' Makefile
    make 2>&1 | tail -3 || true
fi
echo "  ✓ rsgeotools-rvtgen3d"

# ---------- OpenSplat (3DGS CPU) ----------
echo ""
echo "[9/9] OpenSplat (3D Gaussian Splatting, CPU build)..."
if [[ ! -x "$TOOLS/OpenSplat/build/simple_trainer" ]]; then
    cd "$TOOLS"
    # libtorch CPU build
    if [[ ! -d "$TOOLS/libtorch" ]]; then
        curl -sL "https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-2.5.1%2Bcpu.zip" -o libtorch.zip
        unzip -q libtorch.zip && rm libtorch.zip
    fi
    GIT_SSL_NO_VERIFY=true git -c http.sslVerify=false clone --depth 1 https://github.com/pierotofy/OpenSplat.git
    cd OpenSplat && mkdir -p build && cd build
    cmake .. -DGPU_RUNTIME=CPU -DCMAKE_PREFIX_PATH="$TOOLS/libtorch" -DOPENSPLAT_BUILD_SIMPLE_TRAINER=ON 2>&1 | tail -3
    make -j1 simple_trainer 2>&1 | tail -3 || true
fi
echo "  ✓ OpenSplat (3DGS CPU)"

# ---------- Symlinks ----------
echo ""
echo "=== Symlinks ==="
ln -sf "$TOOLS/blender-4.2.5-linux-x64/blender" /usr/local/bin/blender
ln -sf "$TOOLS/Godot_v4.3-stable_linux.x86_64" /usr/local/bin/godot
ln -sf "$TOOLS/colibri/c/colibri" /usr/local/bin/colibri
ln -sf "$TOOLS/colibri/c/coli" /usr/local/bin/coli
ln -sf "$TOOLS/TerraForge3D" /usr/local/bin/terraforge3d
ln -sf "$TOOLS/OpenSplat/build/simple_trainer" /usr/local/bin/opensplat
ln -sf "$TOOLS/rsgeotools/bin/rsgeotools-rvtgen3d" /usr/local/bin/rsgeotools-rvtgen3d

# ---------- Doctor ----------
echo ""
echo "=== DOCTOR CHECK ==="
for cmd in blender godot colibri coli opensplat terraforge3d rsgeotools-rvtgen3d colmap osmconvert gdalinfo java; do
    if command -v $cmd >/dev/null 2>&1; then
        echo "  ✓ $cmd: $(command -v $cmd)"
    else
        echo "  ✗ $cmd"
    fi
done

echo ""
echo "=== DONE — log: $LOG ==="
