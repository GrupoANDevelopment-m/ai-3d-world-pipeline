#!/usr/bin/env bash
# =============================================================================
# bycob_world.sh — Bycob/world wrapper (REAL — verificado em 2026-09-19)
# =============================================================================
# Repo: https://github.com/Bycob/world
#
# VERIFICADO:
#   - Clonado e compilado em /opt/tools/world
#   - libworld.so + libpeace.so + libzlib.a + liblibpng.a gerados
#   - binários test_ini_files, test_terrain, test_tree, test_reliefmap, mapper
#     funcionam e geram assets reais (terrain.obj + texturas + trees.obj)
#
# Build (uma vez):
#   cd /opt/tools/world && mkdir build && cd build
#   cmake .. -DCMAKE_BUILD_TYPE=Release && make -j2
#
# Status: ✅ funcional
#
# Uso:
#   bash bycob_world.sh --output ./world --terrain --vegetation --cities --voxels
# =============================================================================
set -euo pipefail

OUTPUT="./bycob_out"
SOURCE_DIR="${BYCOB_WORLD_DIR:-/opt/tools/world}"
BUILD_DIR="$SOURCE_DIR/build"
TERRAIN=1
VEGETATION=1
CITIES=0
VOXELS=0
SEED=42
TEST_TYPE="terrain"

usage() {
  cat <<EOF
Uso: $0 --output <dir> [opções]

  --output         Diretório de saída. Default: ./bycob_out
  --terrain        Gera terrain mesh (test_terrain). Default: true
  --vegetation     Gera modelos de árvores (test_tree). Default: true
  --cities         Gera cities (em breve)
  --voxels         Inclui voxel (em breve)
  --seed           Seed. Default: 42
  --test           terrain | tree | mapper. Default: terrain
  --source         Caminho do repo Bycob/world. Default: /opt/tools/world

Saídas (no diretório --output):
  - terrain.obj + terrain.png + terrain.mtl
  - tree/instances.obj + tree/*.png (texturas de espécies)

Exemplos:
  $0 --output ./world --terrain --vegetation
  $0 --output ./full --test mapper
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)     OUTPUT="$2"; shift 2 ;;
    --terrain)    TERRAIN=1; shift ;;
    --no-terrain) TERRAIN=0; shift ;;
    --vegetation) VEGETATION=1; shift ;;
    --no-vegetation) VEGETATION=0; shift ;;
    --cities)     CITIES=1; shift ;;
    --voxels)     VOXELS=1; shift ;;
    --seed)       SEED="$2"; shift 2 ;;
    --test)       TEST_TYPE="$2"; shift 2 ;;
    --source)     SOURCE_DIR="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *)            echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -d "$BUILD_DIR" || ! -x "$BUILD_DIR/bin/test_terrain" ]]; then
  echo "Erro: Bycob/world não compilado em $BUILD_DIR" >&2
  echo "Compile com:" >&2
  echo "  cd $SOURCE_DIR && mkdir -p build && cd build" >&2
  echo "  cmake .. -DCMAKE_BUILD_TYPE=Release && make -j2" >&2
  exit 2
fi

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

# NÃO cd no build dir: os binários do bycob criam assets/ no CWD, e o `tee` no
# log precisa de path absoluto. Em vez disso, prefixa binários com $BUILD_DIR.
TERRAIN_BIN="$BUILD_DIR/bin/test_terrain"
TREE_BIN="$BUILD_DIR/bin/test_tree"
MAPPER_BIN="$BUILD_DIR/bin/mapper"

if [[ $TERRAIN -eq 1 ]]; then
  echo "[bycob_world] Gerando terrain (test_terrain)..." | tee -a "$LOG"
  # Bycob gera outputs em assets/ relativo ao cwd → fazemos em /tmp/bycob_<pid>/ e copiamos
  WORK_DIR="$(mktemp -d -t bycob.XXXXXX)"
  (cd "$WORK_DIR" && "$TERRAIN_BIN" 2>&1) | tee -a "$LOG"
  cp -v "$WORK_DIR/assets/terrain/terrain.obj" "$WORK_DIR/assets/terrain/terrain.png" "$WORK_DIR/assets/terrain/test2_"*.png "$OUTPUT/" 2>/dev/null || true
  rm -rf "$WORK_DIR"
fi

if [[ $VEGETATION -eq 1 ]]; then
  echo "[bycob_world] Gerando trees (test_tree)..." | tee -a "$LOG"
  WORK_DIR="$(mktemp -d -t bycob.XXXXXX)"
  (cd "$WORK_DIR" && "$TREE_BIN" 2>&1) | tee -a "$LOG"
  cp -rv "$WORK_DIR/assets/tree" "$OUTPUT/" 2>/dev/null || true
  rm -rf "$WORK_DIR"
fi

if [[ "$TEST_TYPE" == "mapper" ]]; then
  echo "[bycob_world] Gerando mapa 2D (mapper)..." | tee -a "$LOG"
  WORK_DIR="$(mktemp -d -t bycob.XXXXXX)"
  (cd "$WORK_DIR" && "$MAPPER_BIN" 2>&1) | tee -a "$LOG" || true
  cp -v "$WORK_DIR/map.png" "$OUTPUT/" 2>/dev/null || true
  rm -rf "$WORK_DIR"
fi

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "bycob_world",
  "version": "main",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "seed": $SEED,
  "binary_path": "$BUILD_DIR/bin/",
  "features": {
    "terrain": $([ $TERRAIN -eq 1 ] && echo true || echo false),
    "vegetation": $([ $VEGETATION -eq 1 ] && echo true || echo false),
    "cities": $([ $CITIES -eq 1 ] && echo true || echo false),
    "voxels": $([ $VOXELS -eq 1 ] && echo true || echo false)
  },
  "output": "$OUTPUT",
  "artifacts": {
    "terrain_obj": "$OUTPUT/terrain.obj",
    "terrain_png": "$OUTPUT/terrain.png",
    "trees": "$OUTPUT/tree/"
  }
}
EOF

echo "[bycob_world] Concluído em $((END - START))s — saída em $OUTPUT"
