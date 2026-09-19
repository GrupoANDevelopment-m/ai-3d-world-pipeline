#!/usr/bin/env bash
# =============================================================================
# terraforge.sh — TerraForge3D wrapper (Jaysmito101/TerraForge3D)
# =============================================================================
# Repo:    https://github.com/Jaysmito101/TerraForge3D
# Releases: https://github.com/Jaysmito101/TerraForge3D/releases/tag/v2.3
#
# Status:  ✅ real (binário CLI disponível a partir do v2.3)
#
# Uso:
#   bash terraforge.sh --biome mountain --size-km 4 --resolution 2048 \
#       --seed 42 --output ./terrain --format glb
# =============================================================================
set -euo pipefail

BIOME="mountain"
SIZE_KM=4
RESOLUTION=2048
SEED=42
EROSION=""
OUTPUT="./terrain"
FORMAT="glb"
PROJECT_FILE=""

usage() {
  cat <<EOF
Uso: $0 [opções]

  --biome        coastal | mountain | desert | forest | tundra | volcanic | grassland
  --size-km      Tamanho do terreno em km (lado). Default: 4
  --resolution   Resolução da heightmap. Default: 2048
  --seed         Seed do gerador. Default: 42
  --erosion      hydraulic | wind | none. Default: hydraulic
  --output       Diretório de saída. Default: ./terrain
  --format       glb | obj | png. Default: glb
  --project      Arquivo de projeto TerraForge3D (.tfp) — opcional

Saídas (em --output):
  - terrain.<format>            ← mesh principal
  - heightmap.png               ← heightmap 16-bit
  - splatmap.png                ← splat PBR (se ativado no projeto)

Exemplos:
  $0 --biome mountain --size-km 4 --resolution 2048 --output ./mt
  $0 --biome coastal --erosion none --format obj
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --biome)      BIOME="$2"; shift 2 ;;
    --size-km)    SIZE_KM="$2"; shift 2 ;;
    --resolution) RESOLUTION="$2"; shift 2 ;;
    --seed)       SEED="$2"; shift 2 ;;
    --erosion)    EROSION="$2"; shift 2 ;;
    --output)     OUTPUT="$2"; shift 2 ;;
    --format)     FORMAT="$2"; shift 2 ;;
    --project)    PROJECT_FILE="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *)            echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

# Detecta o binário
TERRAFORGE_BIN="${TERRAFORGE_BIN:-terraforge}"
if ! command -v "$TERRAFORGE_BIN" >/dev/null 2>&1; then
  echo "Erro: binário 'terraforge' não encontrado no PATH." >&2
  echo "Baixe: https://github.com/Jaysmito101/TerraForge3D/releases/tag/v2.3" >&2
  echo "Ou defina TERRAFORGE_BIN=/path/to/terraforge" >&2
  exit 2
fi

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

echo "[terraforge.sh] Gerando terreno: biome=$BIOME size=${SIZE_KM}km res=${RESOLUTION}x${RESOLUTION} seed=$SEED" | tee -a "$LOG"

# Constrói comando real da CLI do TerraForge3D
ARGS=(
  generate
  --biome "$BIOME"
  --size-km "$SIZE_KM"
  --resolution "$RESOLUTION"
  --seed "$SEED"
  --output-dir "$OUTPUT"
  --export-format "$FORMAT"
)
[[ -n "$EROSION" && "$EROSION" != "none" ]] && ARGS+=(--erosion "$EROSION")

# Se houver projeto .tfp, prefere o pipeline do projeto
if [[ -n "$PROJECT_FILE" && -f "$PROJECT_FILE" ]]; then
  ARGS=(--project "$PROJECT_FILE" --output-dir "$OUTPUT" --export-format "$FORMAT")
fi

"$TERRAFORGE_BIN" "${ARGS[@]}" 2>&1 | tee -a "$LOG"

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "terraforge3d",
  "version": "v2.3",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "biome": "$BIOME",
  "size_km": $SIZE_KM,
  "resolution": $RESOLUTION,
  "seed": $SEED,
  "erosion": "$EROSION",
  "format": "$FORMAT",
  "artifacts": {
    "mesh": "$OUTPUT/terrain.${FORMAT}",
    "heightmap": "$OUTPUT/heightmap.png",
    "splatmap": "$OUTPUT/splatmap.png"
  }
}
EOF

echo "[terraforge.sh] Concluído em $((END - START))s — saída em $OUTPUT"
