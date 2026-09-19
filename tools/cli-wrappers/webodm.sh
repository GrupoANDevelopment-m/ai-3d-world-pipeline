#!/usr/bin/env bash
# =============================================================================
# webodm.sh — OpenDroneMap wrapper (georreferenciamento + ortofoto)
# =============================================================================
# Uso:
#   bash webodm.sh --photos ./input/ --output ./output/ [--gcp ./gcps.txt] [--endpoint http://localhost:8000]
# =============================================================================
set -euo pipefail

PHOTOS=""
OUTPUT=""
GCP=""
ENDPOINT="${WEBODM_ENDPOINT:-http://localhost:8000}"
TOKEN="${WEBODM_TOKEN:-}"

usage() {
  cat <<EOF
Uso: $0 --photos <dir> --output <dir> [opções]

  --photos      Diretório com fotos de drone (com GPS)
  --output      Diretório de saída (ortofoto, DEM, LAZ)
  --gcp         Arquivo de Ground Control Points (opcional)
  --endpoint    Endpoint WebODM. Default: http://localhost:8000

Variáveis de ambiente:
  WEBODM_TOKEN  Token de API (recomendado)
  WEBODM_ENDPOINT Endpoint custom

Exemplos:
  $0 --photos ./drone_tiles/ --output ./farm_ortho/ --gcp ./gcps.txt
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --photos)    PHOTOS="$2"; shift 2 ;;
    --output)    OUTPUT="$2"; shift 2 ;;
    --gcp)       GCP="$2"; shift 2 ;;
    --endpoint)  ENDPOINT="$2"; shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *)           echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$PHOTOS" || -z "$OUTPUT" ]] && { echo "Erro: --photos e --output obrigatórios." >&2; usage; exit 1; }

mkdir -p "$OUTPUT"

if command -v docker >/dev/null 2>&1; then
  echo "[webodm.sh] Usando Docker"
  docker run -ti --rm \
      -v "$(realpath "$PHOTOS"):/datasets/input" \
      -v "$(realpath "$OUTPUT"):/datasets/output" \
      opendronemap/odm \
      --project-path /datasets project_new
else
  echo "Erro: Docker não encontrado. WebODM requer Docker." >&2
  echo "Ou use a API REST diretamente com --endpoint." >&2
  exit 2
fi

cat > "$OUTPUT/meta.json" <<EOF
{
  "tool": "webodm",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "input": "$PHOTOS",
  "output": "$OUTPUT",
  "endpoint": "$ENDPOINT",
  "gcp_used": $([ -n "$GCP" ] && echo true || echo false)
}
EOF
