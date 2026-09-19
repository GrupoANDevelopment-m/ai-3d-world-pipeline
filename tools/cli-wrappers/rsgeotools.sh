#!/usr/bin/env bash
# =============================================================================
# rsgeotools.sh — rsgeotools / rvtgen3d wrapper (OSM → 3D)
# =============================================================================
# Repo: https://github.com/romanshuvalov/rsgeotools
#
# Status: ✅ real (CLI: rsgeotools-rvtgen3d).
#
# Uso:
#   bash rsgeotools.sh --x 8580 --y 5611 --w 2 --h 2 \
#       --cache-dir /data/rvt_gpak --output-dir ./lisbon
#
# ⚠️ A preparação do cache (planet, waterpoly) é feita uma vez e demora
#    horas/dias. Veja README do repo.
# =============================================================================
set -euo pipefail

# Coordenadas de tile (OpenStreetMap, zoom 14)
X=""
Y=""
W=1
H=1
CACHE_DIR=""
OUTPUT_DIR="./rsgeotools_out"
DATA_DIR="${RVTGEN3D_DATA:-$HOME/rvtgen3d-data}"
DISABLE_TIMESTAMP=0
FLAT_TERRAIN=0
Z_UP=0
MERGE=0
MERGE_OUTPUT=""
FORMAT="ply"           # ply | obj

usage() {
  cat <<EOF
Uso: $0 --x <int> --y <int> --w <int> --h <int> --cache-dir <dir> [opções]

  --x        Coordenada X do tile no zoom 14
  --y        Coordenada Y do tile no zoom 14
  --w        Largura do retângulo em tiles. Default: 1
  --h        Altura do retângulo em tiles. Default: 1
  --cache-dir   Diretório RVT_GPAK_DIR (saída do planet-process)
  --output-dir  Diretório de saída. Default: ./rsgeotools_out
  --data-dir    Diretório rvtgen3d-data. Default: \$RVTGEN3D_DATA ou ~/rvtgen3d-data
  --disable-timestamp  Desabilita criação de pasta única por timestamp
  --flat-terrain       Desabilita relevo (terreno plano)
  --z-up               Eixo Z vertical (default Y)
  --merge              Mescla todos os tiles em um único arquivo
  --obj                Saída em OBJ em vez de PLY

Saídas (camadas 0–8):
  0: surface  1: buildings  2: surface_map  3: roads/rivers
  4: naturals 5: props  6: wires  7: stripes  8: walls

Exemplo:
  $0 --x 8580 --y 5611 --w 2 --h 2 \\
     --cache-dir /data/rvt_gpak --output-dir ./lisbon
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --x)            X="$2"; shift 2 ;;
    --y)            Y="$2"; shift 2 ;;
    --w)            W="$2"; shift 2 ;;
    --h)            H="$2"; shift 2 ;;
    --cache-dir)    CACHE_DIR="$2"; shift 2 ;;
    --output-dir)   OUTPUT_DIR="$2"; shift 2 ;;
    --data-dir)     DATA_DIR="$2"; shift 2 ;;
    --disable-timestamp) DISABLE_TIMESTAMP=1; shift ;;
    --flat-terrain) FLAT_TERRAIN=1; shift ;;
    --z-up)         Z_UP=1; shift ;;
    --merge)        MERGE=1; shift ;;
    --obj)          FORMAT="obj"; shift ;;
    -h|--help)      usage; exit 0 ;;
    *)              echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$X" || -z "$Y" || -z "$CACHE_DIR" ]] && {
  echo "Erro: --x, --y e --cache-dir são obrigatórios." >&2
  usage; exit 1
}

if ! command -v rsgeotools-rvtgen3d >/dev/null 2>&1; then
  echo "Erro: rsgeotools-rvtgen3d não encontrado no PATH." >&2
  echo "Compile do repo: https://github.com/romanshuvalov/rsgeotools" >&2
  echo "Deps: libgeos_c, gdal, libtiff-dev, geotiff-bin, osmctools, boost, zlib" >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"
LOG="$OUTPUT_DIR/run.log"
META="$OUTPUT_DIR/meta.json"
START=$(date +%s)

ARGS=(
  --x="$X" --y="$Y"
  --w="$W" --h="$H"
  --cache-dir="$CACHE_DIR"
  --output-dir="$OUTPUT_DIR"
  --data-dir="$DATA_DIR"
  --$FORMAT
)
[[ $DISABLE_TIMESTAMP -eq 1 ]] && ARGS+=(--disable-timestamp-folders)
[[ $FLAT_TERRAIN -eq 1 ]] && ARGS+=(--flat-terrain)
[[ $Z_UP -eq 1 ]] && ARGS+=(--z-up)
[[ $MERGE -eq 1 ]] && ARGS+=(--merge)

echo "[rsgeotools.sh] Gerando tiles x=$X y=$Y w=$W h=$H" | tee -a "$LOG"
rsgeotools-rvtgen3d "${ARGS[@]}" 2>&1 | tee -a "$LOG"

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "rsgeotools",
  "version": "main",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "tile_x": $X, "tile_y": $Y,
  "tiles_w": $W, "tiles_h": $H,
  "cache_dir": "$CACHE_DIR",
  "output_dir": "$OUTPUT_DIR",
  "format": "$FORMAT",
  "layers": ["surface", "buildings", "surface_map", "roads_rivers",
             "naturals", "props", "wires", "stripes", "walls"]
}
EOF

echo "[rsgeotools.sh] Concluído em $((END - START))s"
