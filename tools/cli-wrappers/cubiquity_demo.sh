#!/bin/bash
# cubiquity_demo.sh — wrapper inteligente do Cubiquity
# https://github.com/DavidWilliams81/cubiquity
#
# Aceita flags simples:
#   --algorithm <algo>    (menger_sponge, fractal_noise, worley_noise, checkerboard)
#   --size <N>            (tamanho em voxels por eixo)
#   --output-dir <DIR>    (diretório de saída)
#   --format <fmt>        (pngs, bin, vox)
#
# Se --algorithm for passado, executa: generate → export
# Senão, passa direto pro cubiquity.

set -e

ALGO=""
SIZE=128
OUTDIR=""
FORMAT="pngs"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --algorithm)
            ALGO="$2"
            shift 2
            ;;
        --size)
            SIZE="$2"
            shift 2
            ;;
        --output-dir)
            OUTDIR="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        *)
            # passa adiante
            break
            ;;
    esac
done

if [[ -z "$OUTDIR" ]]; then
    OUTDIR="/workspace/ai-3d-world-pipeline/outputs/cubiquity_default"
fi

mkdir -p "$OUTDIR"

if [[ -n "$ALGO" ]]; then
    name="${ALGO%_*}"   # menger_sponge -> menger
    dag="$OUTDIR/${name}.dag"
    echo "[cubiquity_demo] generating $ALGO size=$SIZE → $dag"
    /workspace/tools/cubiquity/build/cubiquity generate --size "$SIZE" "$ALGO" "$dag"
    echo "[cubiquity_demo] exporting $FORMAT → $OUTDIR/${name}_$FORMAT"
    mkdir -p "$OUTDIR/${name}_$FORMAT"
    /workspace/tools/cubiquity/build/cubiquity export "$FORMAT" "$dag" "$OUTDIR/${name}_$FORMAT"
    echo "[cubiquity_demo] OK"
    echo "$OUTDIR/${name}_$FORMAT"
else
    exec /workspace/tools/cubiquity/build/cubiquity "$@"
fi
