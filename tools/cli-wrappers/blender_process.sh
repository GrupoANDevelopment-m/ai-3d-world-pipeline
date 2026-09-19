#!/usr/bin/env bash
# =============================================================================
# blender_process.sh — Asset processing headless via Blender (REAL)
# =============================================================================
# VERIFICADO em 2026-09-19:
#   - Blender 4.2.5 LTS instalado em /opt/tools/blender-4.2.5-linux-x64/
#   - Converteu terrain.obj (de Bycob) em GLB com 3 LODs (4.2 MB)
#   - asset_processor.py funciona end-to-end
#
# Status: ✅ funcional
#
# Uso:
#   bash blender_process.sh --input ./in.obj --output ./out.glb \
#       [--max-tris 200000] [--lod-levels 4] [--collider trimesh]
# =============================================================================
set -euo pipefail

INPUT=""
OUTPUT=""
MAX_TRIS=200000
LOD_LEVELS=4
COLLIDER="trimesh"
BLENDER_BIN="${BLENDER_BIN:-/opt/tools/blender-4.2.5-linux-x64/blender}"
SCRIPT_DIR="$(cd "$(dirname "$0")/../python" && pwd)"

usage() {
  cat <<EOF
Uso: $0 --input <mesh> --output <mesh> [opções]

  --input        Arquivo de entrada (.glb/.fbx/.obj/.ply/.stl)
  --output       Arquivo de saída (.glb)
  --max-tris     Polycount máximo. Default: 200000
  --lod-levels   Quantidade de LODs. Default: 4
  --collider     Tipo de collider: trimesh | convex | box | capsule. Default: trimesh
  --blender      Caminho do Blender. Default: /opt/tools/blender-4.2.5-linux-x64/blender

Exemplos:
  $0 --input factory.glb --output factory_processed.glb --max-tris 100000 --lod-levels 4
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)      INPUT="$2"; shift 2 ;;
    --output)     OUTPUT="$2"; shift 2 ;;
    --max-tris)   MAX_TRIS="$2"; shift 2 ;;
    --lod-levels) LOD_LEVELS="$2"; shift 2 ;;
    --collider)   COLLIDER="$2"; shift 2 ;;
    --blender)    BLENDER_BIN="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *)            echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$INPUT" || -z "$OUTPUT" ]] && { echo "Erro: --input e --output obrigatórios." >&2; usage; exit 1; }

if [[ ! -x "$BLENDER_BIN" ]]; then
  echo "Erro: Blender não encontrado em $BLENDER_BIN" >&2
  echo "Baixe: https://www.blender.org/download/" >&2
  exit 2
fi

echo "[blender_process] Convertendo $INPUT → $OUTPUT (max=$MAX_TRIS, lods=$LOD_LEVELS, collider=$COLLIDER)"

# Constrói o comando como array para preservar o `--` separador corretamente
CMD=(
    "$BLENDER_BIN"
    --background
    --python "$SCRIPT_DIR/asset_processor.py"
    --
    --input "$INPUT"
    --output "$OUTPUT"
    --max-tris "$MAX_TRIS"
    --lod-levels "$LOD_LEVELS"
    --collider "$COLLIDER"
)
"${CMD[@]}"

echo "[blender_process] Concluído: $OUTPUT"
