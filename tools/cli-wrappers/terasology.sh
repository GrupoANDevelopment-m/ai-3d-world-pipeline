#!/usr/bin/env bash
# =============================================================================
# terasology.sh — Terasology (MovingBlocks/Terasology) wrapper
# =============================================================================
# Repo: https://github.com/MovingBlocks/Terasology
# Site:  https://terasology.org
#
# Status: ✅ real (Launcher ou build direto).
# Modo headless via Gradle: ./gradlew run -Pheadless=true
#
# Uso:
#   bash terasology.sh --output ./world_export --seed 42 --module engine
# =============================================================================
set -euo pipefail

OUTPUT="./terasology_out"
SEED=42
MODULES="CoreWorlds,CoreAssets,City"
HEADLESS=1
TERASOLOGY_DIR="${TERASOLOGY_DIR:-$HOME/Terasology}"

usage() {
  cat <<EOF
Uso: $0 --output <dir> --seed <int> [opções]

  --output      Diretório de saída (world export)
  --seed        Seed de geração. Default: 42
  --modules     Lista de módulos (vírgula). Default: CoreWorlds,CoreAssets,City
  --no-headless Desabilita modo headless
  --source      Caminho do repo Terasology. Default: \$TERASOLOGY_DIR ou ~/Terasology

Exemplos:
  $0 --output ./world --seed 42 --modules CoreWorlds,CoreAssets
  $0 --output ./voxel_city --modules City,CoreWorlds
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)      OUTPUT="$2"; shift 2 ;;
    --seed)        SEED="$2"; shift 2 ;;
    --modules)     MODULES="$2"; shift 2 ;;
    --no-headless) HEADLESS=0; shift ;;
    --source)      TERASOLOGY_DIR="$2"; shift 2 ;;
    -h|--help)     usage; exit 0 ;;
    *)             echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -d "$TERASOLOGY_DIR" ]]; then
  echo "Erro: repo Terasology não encontrado em $TERASOLOGY_DIR" >&2
  echo "Baixe: https://terasology.org/downloads/" >&2
  echo "Ou clone: git clone https://github.com/MovingBlocks/Terasology" >&2
  exit 2
fi

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

# Garante módulos (clone em ./modules/)
MODULES_DIR="$TERASOLOGY_DIR/modules"
mkdir -p "$MODULES_DIR"
IFS=',' read -ra MOD_ARR <<< "$MODULES"
for mod in "${MOD_ARR[@]}"; do
  if [[ ! -d "$MODULES_DIR/$mod" ]]; then
    echo "[terasology.sh] Clonando módulo: $mod" | tee -a "$LOG"
    git clone "https://github.com/Terasology/$mod" "$MODULES_DIR/$mod" 2>&1 | tee -a "$LOG"
  fi
done

echo "[terasology.sh] Iniciando Terasology (seed=$SEED, headless=$HEADLESS)" | tee -a "$LOG"

ARGS=(run -Pseed="$SEED")
[[ $HEADLESS -eq 1 ]] && ARGS+=(-Pheadless=true)

cd "$TERASOLOGY_DIR"
./gradlew "${ARGS[@]}" 2>&1 | tee -a "$LOG" &
PID=$!

# Captura por X segundos
TIMEOUT="${TERASOLOGY_TIMEOUT:-600}"
sleep "$TIMEOUT" && kill $PID 2>/dev/null || true

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "terasology",
  "version": "Omega",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "seed": $SEED,
  "modules": "$MODULES",
  "headless": $([ $HEADLESS -eq 1 ] && echo true || echo false),
  "output": "$OUTPUT"
}
EOF

echo "[terasology.sh] Captura finalizada em $((END - START))s"
