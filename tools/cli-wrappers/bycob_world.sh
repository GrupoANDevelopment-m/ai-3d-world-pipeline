#!/usr/bin/env bash
# =============================================================================
# bycob_world.sh — Bycob/world wrapper (C++ library)
# =============================================================================
# Repo: https://github.com/Bycob/world
#
# Status: ✅ real (compila com CMake + opcional Vulkan/Irrlicht).
#
# Uso:
#   bash bycob_world.sh --output ./world --terrain --vegetation --cities
# =============================================================================
set -euo pipefail

OUTPUT="./bycob_out"
TERRAIN=1
VEGETATION=1
CITIES=0
VOXELS=0
SEED=42
SOURCE_DIR="${BYCOB_WORLD_DIR:-$HOME/world}"

usage() {
  cat <<EOF
Uso: $0 --output <dir> [opções]

  --output         Diretório de saída. Default: ./bycob_out
  --terrain        Inclui geração de terreno. Default: true
  --vegetation     Inclui vegetação. Default: true
  --cities         Inclui cidades. Default: false
  --voxels         Inclui voxel (estilo Minecraft). Default: false
  --seed           Seed. Default: 42
  --source         Caminho do repo Bycob/world. Default: \$BYCOB_WORLD_DIR ou ~/world

Exemplos:
  $0 --output ./world --terrain --vegetation
  $0 --output ./full --terrain --vegetation --cities --voxels
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
    --source)     SOURCE_DIR="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *)            echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Erro: repo Bycob/world não encontrado em $SOURCE_DIR" >&2
  echo "Clone: git clone https://github.com/Bycob/world" >&2
  exit 2
fi

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

BUILD_DIR="$SOURCE_DIR/build"
if [[ ! -d "$BUILD_DIR" ]]; then
  echo "[bycob_world.sh] Compilando Bycob/world (cmake + make)..." | tee -a "$LOG"
  mkdir -p "$BUILD_DIR"
  (cd "$BUILD_DIR" && cmake "$SOURCE_DIR" && make -j$(nproc)) 2>&1 | tee -a "$LOG"
fi

DEMO_BIN="$BUILD_DIR/WorldDemo"
[[ -f "$BUILD_DIR/world_demo" ]] && DEMO_BIN="$BUILD_DIR/world_demo"
[[ -f "$BUILD_DIR/Peace" ]] && DEMO_BIN="$BUILD_DIR/Peace"

if [[ ! -x "$DEMO_BIN" ]]; then
  echo "Erro: binário demo não encontrado em $BUILD_DIR." >&2
  echo "Procure por 'world_demo', 'WorldDemo', ou 'Peace'." >&2
  exit 2
fi

ARGS=(--output "$OUTPUT" --seed "$SEED")
[[ $TERRAIN -eq 1 ]]    && ARGS+=(--terrain)
[[ $VEGETATION -eq 1 ]] && ARGS+=(--vegetation)
[[ $CITIES -eq 1 ]]     && ARGS+=(--cities)
[[ $VOXELS -eq 1 ]]     && ARGS+=(--voxels)

echo "[bycob_world.sh] Rodando demo: ${ARGS[*]}" | tee -a "$LOG"
"$DEMO_BIN" "${ARGS[@]}" 2>&1 | tee -a "$LOG"

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "bycob_world",
  "version": "main",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "seed": $SEED,
  "features": {
    "terrain": $([ $TERRAIN -eq 1 ] && echo true || echo false),
    "vegetation": $([ $VEGETATION -eq 1 ] && echo true || echo false),
    "cities": $([ $CITIES -eq 1 ] && echo true || echo false),
    "voxels": $([ $VOXELS -eq 1 ] && echo true || echo false)
  },
  "output": "$OUTPUT"
}
EOF

echo "[bycob_world.sh] Concluído em $((END - START))s"
