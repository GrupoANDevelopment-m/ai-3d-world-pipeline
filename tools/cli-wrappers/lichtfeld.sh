#!/usr/bin/env bash
# =============================================================================
# lichtfeld.sh — 3D Gaussian Splatting (LichtFeld Studio)
# =============================================================================
# Uso:
#   bash lichtfeld.sh --photos ./input/ --output ./output/ [--iter 30000] [--sh 3]
# =============================================================================
set -euo pipefail

PHOTOS=""
OUTPUT=""
ITER=30000
SH=3
RES="1920x1080"
COMPRESS="ksplat"

usage() {
  cat <<EOF
Uso: $0 --photos <dir> --output <dir> [opções]

  --photos       Diretório com fotos
  --output       Diretório de saída
  --iter         Iterações de treinamento. Default: 30000
  --sh           Spherical Harmonics degree (0-3). Default: 3
  --resolution   Resolução de treinamento. Default: 1920x1080
  --compress     Formato de compressão: ksplat | spz | splat | none. Default: ksplat

Exemplos:
  $0 --photos ./drone_photos/ --output ./factory_splat/
  $0 --photos ./holiday/ --output ./holiday_splat/ --iter 50000 --sh 3
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --photos)     PHOTOS="$2"; shift 2 ;;
    --output)     OUTPUT="$2"; shift 2 ;;
    --iter)       ITER="$2"; shift 2 ;;
    --sh)         SH="$2"; shift 2 ;;
    --resolution) RES="$2"; shift 2 ;;
    --compress)   COMPRESS="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *)            echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$PHOTOS" || -z "$OUTPUT" ]] && { echo "Erro: --photos e --output obrigatórios." >&2; usage; exit 1; }

if ! command -v lichtfeld >/dev/null 2>&1; then
  echo "Erro: LichtFeld Studio não encontrado." >&2
  echo "Baixe: https://github.com/RobertKrajewski/LichtFeld-Studio" >&2
  exit 2
fi

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

echo "[lichtfeld.sh] Treinando 3DGS — ${ITER} iterações, SH=${SH}, res=${RES}" | tee -a "$LOG"

lichtfeld train \
    --data "$PHOTOS" \
    --output "$OUTPUT/scene.ply" \
    --iterations "$ITER" \
    --sh-degree "$SH" \
    --resolution "$RES" \
    2>&1 | tee -a "$LOG"

# Compressão
case "$COMPRESS" in
  ksplat)
    if command -v splat-tool >/dev/null 2>&1; then
      splat-tool compress --input "$OUTPUT/scene.ply" --output "$OUTPUT/scene.ksplat" --quality high
    else
      echo "[lichtfeld.sh] Aviso: splat-tool não disponível, mantendo .ply"
      COMPRESS="none"
    fi
    ;;
  spz)
    if command -v spz-encode >/dev/null 2>&1; then
      spz-encode --input "$OUTPUT/scene.ply" --output "$OUTPUT/scene.spz"
    else
      echo "[lichtfeld.sh] Aviso: spz-encode não disponível"
      COMPRESS="none"
    fi
    ;;
  splat)
    if command -v splat-convert >/dev/null 2>&1; then
      splat-convert --input "$OUTPUT/scene.ply" --output "$OUTPUT/scene.splat"
    fi
    ;;
  none) ;;
  *) echo "Compressão desconhecida: $COMPRESS" >&2; exit 1 ;;
esac

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "lichtfeld",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "input": "$PHOTOS",
  "output": "$OUTPUT",
  "iterations": $ITER,
  "sh_degree": $SH,
  "compression": "$COMPRESS",
  "artifacts": {
    "ply": "$OUTPUT/scene.ply",
    "compressed": "$OUTPUT/scene.${COMPRESS}"
  }
}
EOF

echo "[lichtfeld.sh] Concluído em $((END - START))s"
