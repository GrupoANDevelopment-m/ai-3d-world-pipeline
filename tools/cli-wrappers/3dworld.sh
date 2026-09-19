#!/usr/bin/env bash
# =============================================================================
# 3dworld.sh — 3DWorld (fegennari/3DWorld) wrapper
# =============================================================================
# Repo: https://github.com/fegennari/3DWorld
#
# Status: ✅ real (engine OpenGL + CLI próprio com config files).
#
# Uso:
#   bash 3dworld.sh --config ./configs/san_miguel.txt --output ./frames/
# =============================================================================
set -euo pipefail

CONFIG=""
OUTPUT="./3dworld_out"
SOURCE_DIR="${THREEDWORLD_DIR:-$HOME/3DWorld}"
HEADLESS="${THREEDWORLD_HEADLESS:-xvfb-run -a}"

usage() {
  cat <<EOF
Uso: $0 --config <config.txt> --output <dir> [opções]

  --config     Arquivo de configuração 3DWorld (obrigatório)
  --output     Diretório de saída. Default: ./3dworld_out
  --source     Caminho do repo 3DWorld. Default: \$THREEDWORLD_DIR ou ~/3DWorld
  --headless   Wrapper headless (default: 'xvfb-run -a'). Use '' para desabilitar.

Exemplos:
  $0 --config ./configs/heightmap.txt --output ./out
  $0 --config ./configs/san_miguel.txt --output ./miguel

Deps: OpenGL 4.5, freeglut, glew, glm, OpenAL, libpng, libtiff, zlib, Assimp.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)   CONFIG="$2"; shift 2 ;;
    --output)   OUTPUT="$2"; shift 2 ;;
    --source)   SOURCE_DIR="$2"; shift 2 ;;
    --headless) HEADLESS="$2"; shift 2 ;;
    -h|--help)  usage; exit 0 ;;
    *)          echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$CONFIG" ]] && { echo "Erro: --config obrigatório." >&2; usage; exit 1; }
[[ ! -f "$CONFIG" ]] && { echo "Erro: config não encontrado: $CONFIG" >&2; exit 1; }
[[ ! -d "$SOURCE_DIR" ]] && {
  echo "Erro: repo 3DWorld não encontrado em $SOURCE_DIR" >&2
  echo "Clone: git clone https://github.com/fegennari/3DWorld" >&2
  exit 2
}

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

BIN="$SOURCE_DIR/3DWorld"
[[ ! -x "$BIN" && -x "$SOURCE_DIR/build/3DWorld" ]] && BIN="$SOURCE_DIR/build/3DWorld"

if [[ ! -x "$BIN" ]]; then
  echo "[3dworld.sh] Compilando 3DWorld (Linux makefile)..." | tee -a "$LOG"
  (cd "$SOURCE_DIR" && make -f makefile -j$(nproc) 2>&1 | tee -a "$LOG") || {
    echo "Erro: build falhou. Tente Visual Studio (Windows) ou make -f makefile.msys2." >&2
    exit 2
  }
fi

CMD=("$BIN" "$CONFIG")
[[ -n "$HEADLESS" ]] && CMD=($HEADLESS "${CMD[@]}")

echo "[3dworld.sh] Rodando: ${CMD[*]}" | tee -a "$LOG"
"${CMD[@]}" 2>&1 | tee -a "$LOG" &
PID=$!

# Roda por no máximo 5 min para gerar um frame de teste, depois mata
# (3DWorld é interativo — para batch processing, ajuste --timeout abaixo)
TIMEOUT="${THREEDWORLD_TIMEOUT:-300}"
sleep "$TIMEOUT" && kill $PID 2>/dev/null || true

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "3dworld",
  "version": "main",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "config": "$CONFIG",
  "output": "$OUTPUT",
  "note": "3DWorld é interativo; este wrapper roda por \$THREEDWORLD_TIMEOUT segundos (default 300)."
}
EOF

echo "[3dworld.sh] Captura finalizada em $((END - START))s"
