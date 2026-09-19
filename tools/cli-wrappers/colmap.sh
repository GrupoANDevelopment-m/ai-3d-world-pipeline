#!/usr/bin/env bash
# =============================================================================
# colmap.sh — Structure-from-Motion + Dense MVS wrapper
# =============================================================================
# Uso:
#   bash colmap.sh --photos ./input/ --output ./output/ [--type dense|sparse] [--gpu]
# =============================================================================
set -euo pipefail

PHOTOS=""
OUTPUT=""
TYPE="dense"
GPU=0
MATCHING="exhaustive"

usage() {
  cat <<EOF
Uso: $0 --photos <dir> --output <dir> [--type sparse|dense] [--gpu] [--matching ...]

  --photos      Diretório com fotos (.jpg/.jpeg/.png/.tif)
  --output      Diretório de saída
  --type        Tipo de reconstrução: sparse (SfM) ou dense (MVS). Default: dense
  --gpu         Usar GPU (requer CUDA). Default: off
  --matching    exhaustive | sequential | vocab_tree. Default: exhaustive

Exemplos:
  $0 --photos ./drone_photos/ --output ./factory_splat/ --type dense --gpu
  $0 --photos ./holiday_pics/ --output ./holiday_3d/ --type sparse
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --photos)    PHOTOS="$2"; shift 2 ;;
    --output)    OUTPUT="$2"; shift 2 ;;
    --type)      TYPE="$2"; shift 2 ;;
    --gpu)       GPU=1; shift ;;
    --matching)  MATCHING="$2"; shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *)           echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$PHOTOS" || -z "$OUTPUT" ]]; then
  echo "Erro: --photos e --output são obrigatórios." >&2
  usage; exit 1
fi

if ! command -v colmap >/dev/null 2>&1; then
  echo "Erro: COLMAP não encontrado no PATH." >&2
  echo "Instale: https://colmap.github.io/install.html" >&2
  exit 2
fi

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

echo "[colmap.sh] $(date -Iseconds) — iniciando reconstrução ($TYPE)" | tee -a "$LOG"

# ---------- Sparse SfM ----------
echo "[colmap.sh] Etapa 1/3 — SfM esparso" | tee -a "$LOG"
colmap automatic_reconstructor \
    --workspace_path "$OUTPUT" \
    --image_path "$PHOTOS" \
    --use_gpu $((GPU)) \
    --mapper_extraction.matcher_type "$MATCHING" \
    2>&1 | tee -a "$LOG"

# ---------- Dense MVS ----------
if [[ "$TYPE" == "dense" ]]; then
  echo "[colmap.sh] Etapa 2/3 — Undistort" | tee -a "$LOG"
  colmap image_undistorter \
      --image_path "$PHOTOS" \
      --input_path "$OUTPUT/sparse/0" \
      --output_path "$OUTPUT/dense" \
      2>&1 | tee -a "$LOG"

  echo "[colmap.sh] Etapa 3/3 — Patch Match Stereo + Fusion" | tee -a "$LOG"
  colmap patch_match_stereo \
      --workspace_path "$OUTPUT/dense" \
      2>&1 | tee -a "$LOG"

  colmap stereo_fusion \
      --workspace_path "$OUTPUT/dense" \
      --output_path "$OUTPUT/dense/fused.ply" \
      2>&1 | tee -a "$LOG"
fi

END=$(date +%s)
DURATION=$((END - START))

# ---------- Meta ----------
REGISTERED=$(colmap image_register --help 2>/dev/null; echo "")
cat > "$META" <<EOF
{
  "tool": "colmap",
  "version": "$(colmap --version 2>/dev/null || echo 'unknown')",
  "type": "$TYPE",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $DURATION,
  "input": "$PHOTOS",
  "output": "$OUTPUT",
  "gpu_used": $GPU,
  "matching": "$MATCHING",
  "artifacts": {
    "sparse_cameras": "$OUTPUT/sparse/0/cameras.bin",
    "sparse_images":  "$OUTPUT/sparse/0/images.bin",
    "sparse_points":  "$OUTPUT/sparse/0/points3D.bin",
    "dense_pointcloud": "$OUTPUT/dense/fused.ply"
  }
}
EOF

echo "[colmap.sh] Concluído em ${DURATION}s — saída em $OUTPUT"
