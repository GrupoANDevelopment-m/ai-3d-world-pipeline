#!/usr/bin/env bash
# =============================================================================
# meshroom.sh — AliceVision Meshroom wrapper
# =============================================================================
# Uso:
#   bash meshroom.sh --photos ./input/ --output ./output/ [--pipeline ./path/to.mg]
# =============================================================================
set -euo pipefail

PHOTOS=""
OUTPUT=""
PIPELINE_FILE=""

usage() {
  cat <<EOF
Uso: $0 --photos <dir> --output <dir> [--pipeline <meshroom.mg>]

  --photos      Diretório com fotos
  --output      Diretório de saída (cache Meshroom)
  --pipeline    Arquivo .mg (pipeline Meshroom). Default: padrão photogrammetry

Exemplos:
  $0 --photos ./input/ --output ./output/
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --photos)    PHOTOS="$2"; shift 2 ;;
    --output)    OUTPUT="$2"; shift 2 ;;
    --pipeline)  PIPELINE_FILE="$2"; shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *)           echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$PHOTOS" || -z "$OUTPUT" ]] && { echo "Erro: --photos e --output obrigatórios." >&2; usage; exit 1; }

if ! command -v meshroom_batch >/dev/null 2>&1 && ! command -v meshroom >/dev/null 2>&1; then
  echo "Erro: Meshroom não encontrado." >&2
  echo "Baixe: https://alicevision.org/#meshroom" >&2
  exit 2
fi

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

if [[ -n "$PIPELINE_FILE" ]]; then
  meshroom_batch --input "$PHOTOS" --output "$OUTPUT" --pipeline "$PIPELINE_FILE"
else
  meshroom_batch --input "$PHOTOS" --output "$OUTPUT"
fi 2>&1 | tee -a "$LOG"

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "meshroom",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "input": "$PHOTOS",
  "output": "$OUTPUT"
}
EOF

echo "[meshroom.sh] Concluído em $((END - START))s"
