#!/usr/bin/env bash
# =============================================================================
# alicevision.sh — AliceVision CLI wrapper (fotogrametria)
# =============================================================================
# Repo: https://github.com/alicevision/AliceVision
# (também usado pelo Meshroom: https://github.com/alicevision/Meshroom)
#
# Status: ✅ real (CLI por nós do pipeline).
#
# Uso:
#   bash alicevision.sh --photos ./input/ --output ./out/ --mesh --texture
# =============================================================================
set -euo pipefail

PHOTOS=""
OUTPUT="./alicevision_out"
MESH=1
TEXTURE=1
DENSE=1
GPU=1

usage() {
  cat <<EOF
Uso: $0 --photos <dir> --output <dir> [opções]

  --photos      Diretório com fotos
  --output      Diretório de saída (cache + resultados)
  --no-mesh     Pula etapa de meshing (só SfM + MVS denso)
  --no-texture  Pula texturização
  --no-dense    Pula reconstrução densa
  --no-gpu      Desabilita GPU

Etapas executadas (na ordem):
  1. cameraInit        Inicializa estrutura de câmeras
  2. featureExtraction Extrai features SIFT
  3. featureMatching   Combina features
  4. incrementalSfM    SfM esparso
  5. prepareDenseScene Prepara cena para MVS denso
  6. depthMapEstimation Estima depth maps
  7. depthMapFiltering  Filtra depth maps
  8. meshing            Malha 3D (se --no-mesh não usado)
  9. meshFiltering      Limpa a malha
 10. texturing          Aplica texturas (se --no-texture não usado)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --photos)      PHOTOS="$2"; shift 2 ;;
    --output)      OUTPUT="$2"; shift 2 ;;
    --no-mesh)     MESH=0; shift ;;
    --no-texture)  TEXTURE=0; shift ;;
    --no-dense)    DENSE=0; shift ;;
    --no-gpu)      GPU=0; shift ;;
    -h|--help)     usage; exit 0 ;;
    *)             echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$PHOTOS" || -z "$OUTPUT" ]] && { echo "Erro: --photos e --output obrigatórios." >&2; usage; exit 1; }

if ! command -v aliceVision_cameraInit >/dev/null 2>&1; then
  echo "Erro: binários AliceVision não encontrados no PATH." >&2
  echo "Instale: https://github.com/alicevision/AliceVision#installation" >&2
  exit 2
fi

mkdir -p "$OUTPUT"/{cache,sfm,dense,mesh}
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

GPU_ARG=()
[[ $GPU -eq 1 ]] && GPU_ARG=(--useGPU)

echo "[alicevision.sh] 1/10 cameraInit" | tee -a "$LOG"
aliceVision_cameraInit -i "$PHOTOS" -o "$OUTPUT/sfm/cameras.sfm" --sensorDatabase "" --defaultCameraModel "0" 2>&1 | tee -a "$LOG"

echo "[alicevision.sh] 2/10 featureExtraction" | tee -a "$LOG"
aliceVision_featureExtraction -i "$OUTPUT/sfm/cameras.sfm" -o "$OUTPUT/sfm/features.fea" "${GPU_ARG[@]}" 2>&1 | tee -a "$LOG"

echo "[alicevision.sh] 3/10 featureMatching" | tee -a "$LOG"
aliceVision_featureMatching -i "$OUTPUT/sfm/features.fea" -o "$OUTPUT/sfm/matches.fma" 2>&1 | tee -a "$LOG"

echo "[alicevision.sh] 4/10 incrementalSfM" | tee -a "$LOG"
aliceVision_incrementalSfM -i "$OUTPUT/sfm/matches.fma" -o "$OUTPUT/sfm/sfm.abc" --refineIntrinsics 1 2>&1 | tee -a "$LOG"

if [[ $DENSE -eq 1 ]]; then
  echo "[alicevision.sh] 5/10 prepareDenseScene" | tee -a "$LOG"
  aliceVision_prepareDenseScene -i "$OUTPUT/sfm/sfm.abc" -o "$OUTPUT/dense" 2>&1 | tee -a "$LOG"

  echo "[alicevision.sh] 6/10 depthMapEstimation" | tee -a "$LOG"
  aliceVision_depthMapEstimation -i "$OUTPUT/dense" -o "$OUTPUT/dense" "${GPU_ARG[@]}" 2>&1 | tee -a "$LOG"

  echo "[alicevision.sh] 7/10 depthMapFiltering" | tee -a "$LOG"
  aliceVision_depthMapFiltering -i "$OUTPUT/dense" -o "$OUTPUT/dense" 2>&1 | tee -a "$LOG"
fi

if [[ $MESH -eq 1 ]]; then
  echo "[alicevision.sh] 8/10 meshing" | tee -a "$LOG"
  aliceVision_meshing -i "$OUTPUT/dense" -o "$OUTPUT/mesh/mesh.obj" 2>&1 | tee -a "$LOG"

  echo "[alicevision.sh] 9/10 meshFiltering" | tee -a "$LOG"
  aliceVision_meshFiltering -i "$OUTPUT/mesh/mesh.obj" -o "$OUTPUT/mesh/mesh_filtered.obj" 2>&1 | tee -a "$LOG"
fi

if [[ $TEXTURE -eq 1 && $MESH -eq 1 ]]; then
  echo "[alicevision.sh] 10/10 texturing" | tee -a "$LOG"
  aliceVision_texturing -i "$OUTPUT/sfm/sfm.abc" -m "$OUTPUT/mesh/mesh_filtered.obj" -o "$OUTPUT/mesh/textured.obj" 2>&1 | tee -a "$LOG"
fi

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "alicevision",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "input": "$PHOTOS",
  "output": "$OUTPUT",
  "mesh_generated": $([ $MESH -eq 1 ] && echo true || echo false),
  "texture_generated": $([ $TEXTURE -eq 1 ] && echo true || echo false),
  "dense_done": $([ $DENSE -eq 1 ] && echo true || echo false),
  "gpu_used": $([ $GPU -eq 1 ] && echo true || echo false)
}
EOF

echo "[alicevision.sh] Concluído em $((END - START))s"
