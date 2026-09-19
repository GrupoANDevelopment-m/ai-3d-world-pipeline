#!/usr/bin/env bash
# =============================================================================
# lichtfeld.sh — LichtFeld Studio wrapper (3D Gaussian Splatting)
# =============================================================================
# Repo: https://lichtfeld.io / https://github.com/RobertKrajewski/LichtFeld-Studio
#
# ⚠️  GPU REQUIRED. Este wrapper é GPU-only.
#
# Inspirado em JustVugg/colibri (c/colibri.c):
#   "GPU support is opt-in via COLI_CUDA=1. Default is dependency-free CPU."
#
# Adaptado pro nosso pipeline:
#   - Antes de tentar rodar, chama tools/colibri_patterns/gpu_gate.py
#   - Se ambiente é CPU-only, exit 2 com mensagem clara
#   - Isso permite que o pipeline_runner saiba pular este stage limpo
#
# Uso:
#   bash lichtfeld.sh --photos ./input/ --output ./output/ [--force]
#
# O flag --force bypassa o gate (útil pra debug em VM com GPU passthrough).
# =============================================================================
set -euo pipefail

PHOTOS=""
OUTPUT=""
ITER=30000
SH=3
RES="1920x1080"
COMPRESS="ksplat"
FORCE=0

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

usage() {
  cat <<EOF
Uso: $0 --photos <dir> --output <dir> [opções]

  --photos       Diretório com fotos
  --output       Diretório de saída
  --iter         Iterações de treinamento. Default: 30000
  --sh           Spherical Harmonics degree (0-3). Default: 3
  --resolution   Resolução de treinamento. Default: 1920x1080
  --compress     Formato de compressão: ksplat | spz | splat | none. Default: ksplat
  --force        Bypassa o gate de GPU (use com cuidado)

⚠️  Este tool REQUER GPU NVIDIA com CUDA. Em ambiente CPU-only, ele faz skip
    com exit code 2 e mensagem clara, para o pipeline continuar.

Exemplos:
  $0 --photos ./drone_photos/ --output ./factory_splat/
  $0 --photos ./holiday/ --output ./splat/ --force    # ignora gate (debug)
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
    --force)      FORCE=1; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$PHOTOS" || -z "$OUTPUT" ]] && { echo "Erro: --photos e --output obrigatórios." >&2; usage; exit 1; }

# Gate de GPU — inspirado em JustVugg/colibri COLI_CUDA pattern
echo "[lichtfeld.sh] Verificando gate de GPU..." >&2
GATE_ARGS=("$REPO_ROOT/tools/colibri_patterns/gpu_gate.py" "lichtfeld")
[[ $FORCE -eq 1 ]] && GATE_ARGS+=("--force")
if ! python3 "${GATE_ARGS[@]}"; then
  echo "" >&2
  echo "[lichtfeld.sh] ══════════════════════════════════════════════════════════" >&2
  echo "[lichtfeld.sh] SKIP: LichtFeld 3DGS training requer GPU NVIDIA/CUDA." >&2
  echo "[lichtfeld.sh] ══════════════════════════════════════════════════════════" >&2
  echo "[lichtfeld.sh] Alternativas para ambiente CPU-only:" >&2
  echo "[lichtfeld.sh]   1. OpenSplat (C++ libtorch CPU, 100x mais lento)" >&2
  echo "[lichtfeld.sh]   2. 3dgs-warp-scratch (Python, NVIDIA Warp CPU)" >&2
  echo "[lichtfeld.sh]   3. Gaussian-LiteSplat (Python puro, Google Colab)" >&2
  echo "[lichtfeld.sh]   4. Aguardar hardware com GPU" >&2
  echo "[lichtfeld.sh] ══════════════════════════════════════════════════════════" >&2
  exit 2
fi

# Gate passed: tenta rodar LichtFeld real
if ! command -v lichtfeld >/dev/null 2>&1; then
  echo "Erro: LichtFeld Studio não encontrado no PATH." >&2
  echo "Baixe: https://lichtfeld.io/" >&2
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
    fi
    ;;
  spz)
    if command -v spz-encode >/dev/null 2>&1; then
      spz-encode --input "$OUTPUT/scene.ply" --output "$OUTPUT/scene.spz"
    fi
    ;;
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
  "compression": "$COMPRESS"
}
EOF

echo "[lichtfeld.sh] Concluído em $((END - START))s"
