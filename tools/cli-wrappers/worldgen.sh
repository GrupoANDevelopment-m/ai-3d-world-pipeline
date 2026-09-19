#!/usr/bin/env bash
# =============================================================================
# worldgen.sh — WorldGen (ZiYang-xie/WorldGen) wrapper
# =============================================================================
# Repo: https://github.com/ZiYang-xie/WorldGen
#
# Status: ✅ real — usa o demo.py oficial como entry point.
#
# Uso:
#   bash worldgen.sh --prompt "cozy bedroom" --output ./bedroom.ply
#   bash worldgen.sh --image ./ref.jpg --output ./from_image.ply
#   bash worldgen.sh --prompt "landscape" --return-mesh --output ./mesh.ply
# =============================================================================
set -euo pipefail

PROMPT=""
IMAGE=""
OUTPUT="./worldgen_out.ply"
RETURN_MESH=0
USE_SHARP=0
MODE="auto"          # auto | t2s | i2s
LOW_VRAM=0
CONDA_ENV="${WORLDGEN_ENV:-worldgen}"

usage() {
  cat <<EOF
Uso: $0 --prompt "..." | --image <path> --output <path> [opções]

  --prompt        Texto descritor (text-to-scene)
  --image         Imagem de referência (image-to-scene)
  --output        Arquivo de saída (.ply). Default: ./worldgen_out.ply
  --return-mesh   Gera mesh em vez de gaussian splat
  --use-sharp     Usa ml-sharp (experimental, melhor qualidade)
  --low-vram      Ativa modo low-VRAM (GPUs <24GB)
  --mode          t2s | i2s | auto. Default: auto (escolhe por argumento)
  --conda-env     Nome do ambiente conda. Default: worldgen

Exemplos:
  $0 --prompt "A beautiful landscape with a river and mountains" \\
     --output ./scene.ply
  $0 --image ./ref.jpg --output ./scene.ply
  $0 --prompt "cozy bedroom" --return-mesh --output ./bedroom.ply
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)      PROMPT="$2"; shift 2 ;;
    --image)       IMAGE="$2"; shift 2 ;;
    --output)      OUTPUT="$2"; shift 2 ;;
    --return-mesh) RETURN_MESH=1; shift ;;
    --use-sharp)   USE_SHARP=1; shift ;;
    --low-vram)    LOW_VRAM=1; shift ;;
    --mode)        MODE="$2"; shift 2 ;;
    --conda-env)   CONDA_ENV="$2"; shift 2 ;;
    -h|--help)     usage; exit 0 ;;
    *)             echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$PROMPT" && -z "$IMAGE" ]]; then
  echo "Erro: --prompt ou --image é obrigatório." >&2
  usage; exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
LOG="$(dirname "$OUTPUT")/run.log"
META="$(dirname "$OUTPUT")/meta.json"
START=$(date +%s)

# Resolve o demo.py — assume clone local de WorldGen em ~/WorldGen ou WORLDGEN_DIR
WORLDGEN_DIR="${WORLDGEN_DIR:-$HOME/WorldGen}"
if [[ ! -f "$WORLDGEN_DIR/demo.py" ]]; then
  echo "Erro: WorldGen não encontrado em $WORLDGEN_DIR" >&2
  echo "Clone: git clone --recursive https://github.com/ZiYang-xie/WorldGen" >&2
  echo "Ou defina WORLDGEN_DIR=/path/to/WorldGen" >&2
  exit 2
fi

# Ativa conda env
if command -v conda >/dev/null 2>&1; then
  PYTHON="conda run -n $CONDA_ENV python"
else
  echo "Aviso: conda não encontrado. Tentando python direto." >&2
  PYTHON="python"
fi

ARGS=("$WORLDGEN_DIR/demo.py")
[[ -n "$PROMPT" ]] && ARGS+=(-p "$PROMPT")
[[ -n "$IMAGE" ]] && ARGS+=(-i "$IMAGE")
[[ $RETURN_MESH -eq 1 ]] && ARGS+=(--return_mesh)
[[ $USE_SHARP -eq 1 ]] && ARGS+=(--use_sharp)
[[ $LOW_VRAM -eq 1 ]] && ARGS+=(--low_vram)

echo "[worldgen.sh] Rodando demo.py em $CONDA_ENV" | tee -a "$LOG"

# Roda dentro do dir do WorldGen para achar imports relativos
(cd "$WORLDGEN_DIR" && $PYTHON "${ARGS[@]}") 2>&1 | tee -a "$LOG"

# O demo.py salva em ./output_<timestamp>/; move para o --output pedido
LATEST=$(ls -td "$WORLDGEN_DIR"/output_* 2>/dev/null | head -1 || true)
if [[ -n "$LATEST" ]]; then
  FINAL="$LATEST/result.ply"
  [[ $RETURN_MESH -eq 1 ]] && FINAL="$LATEST/result_mesh.ply"
  [[ -f "$FINAL" ]] && mv "$FINAL" "$OUTPUT"
fi

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "worldgen",
  "version": "main",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "mode": "$MODE",
  "prompt": "$PROMPT",
  "image": "$IMAGE",
  "return_mesh": $([ $RETURN_MESH -eq 1 ] && echo true || echo false),
  "use_sharp": $([ $USE_SHARP -eq 1 ] && echo true || echo false),
  "output": "$OUTPUT"
}
EOF

echo "[worldgen.sh] Concluído em $((END - START))s — saída em $OUTPUT"
