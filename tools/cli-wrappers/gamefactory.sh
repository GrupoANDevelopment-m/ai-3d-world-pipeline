#!/usr/bin/env bash
# =============================================================================
# gamefactory.sh — GameFactory-3A (OpenDCAI/GameFactory-3A) wrapper
# =============================================================================
# Repo: https://github.com/OpenDCAI/GameFactory-3A
#
# GameFactory-3A é um framework de skills/pipelines para coding agents.
# Não tem CLI próprio — o agente (Codex/Claude Code/Gemini CLI) lê
# agent_skills/setting_overview.md e dispara as pipelines via Python.
#
# Este wrapper facilita a chamada via shell usando os entry points Python
# das pipelines oficiais.
#
# Status: ✅ real (wraps os entry points do repo).
#
# Uso:
#   bash gamefactory.sh gen_3d_object --type tree --output ./tree.glb
#   bash gamefactory.sh gen_3d_scene --prompt "forest" --output ./scene/
#   bash gamefactory.sh gen_audio --prompt "rain" --output ./rain.wav
# =============================================================================
set -euo pipefail

SUBCMD="${1:-}"
shift || true

usage() {
  cat <<EOF
Uso: $0 <subcommand> [opções]

Subcomandos:
  gen_3d_object    Gera objeto 3D individual (prop, arma, mesh)
  gen_3d_scene     Gera cena 3D (interior reconstruído ou ambiente montado)
  gen_motion       Gera motion / animação
  gen_audio        Gera áudio (diálogo, SFX, ambience)
  gen_cg_video     Gera vídeo CG
  gen_tpose_image  Gera imagem T-pose para personagem

Opções comuns:
  --prompt         Texto descritor
  --output         Caminho de saída
  --type           Tipo (para gen_3d_object)
  --engine         godot4 | unity | ue5 | blender. Default: godot4
  --repo           Caminho do GameFactory-3A. Default: \$GAMEFACTORY_DIR ou ./GameFactory-3A

Exemplos:
  $0 gen_3d_object --type tree --output ./tree.glb
  $0 gen_3d_scene --prompt "medieval forest" --output ./forest/
EOF
}

if [[ -z "$SUBCMD" || "$SUBCMD" == "-h" || "$SUBCMD" == "--help" ]]; then
  usage; exit 0
fi

ENGINE="godot4"
PROMPT=""
OUTPUT=""
TYPE=""
GAMEFACTORY_DIR="${GAMEFACTORY_DIR:-./GameFactory-3A}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt) PROMPT="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --type)   TYPE="$2"; shift 2 ;;
    --engine) ENGINE="$2"; shift 2 ;;
    --repo)   GAMEFACTORY_DIR="$2"; shift 2 ;;
    *)        echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -d "$GAMEFACTORY_DIR" ]]; then
  echo "Erro: GameFactory-3A não encontrado em $GAMEFACTORY_DIR" >&2
  echo "Clone: git clone https://github.com/OpenDCAI/GameFactory-3A" >&2
  echo "Ou: GAMEFACTORY_DIR=/path/to/GameFactory-3A $0 ..." >&2
  exit 2
fi

PIPELINE_DIR="$GAMEFACTORY_DIR/pipeline"
SKILL_FILE="$GAMEFACTORY_DIR/agent_skills/setting_overview.md"

if [[ ! -f "$SKILL_FILE" ]]; then
  echo "Erro: $SKILL_FILE não encontrado. Repo pode estar corrompido." >&2
  exit 2
fi

case "$SUBCMD" in
  gen_3d_object)
    PIPELINE="$PIPELINE_DIR/assets_gen/gen_3d_object"
    ;;
  gen_3d_scene)
    PIPELINE="$PIPELINE_DIR/assets_gen/gen_3d_scene"
    ;;
  gen_motion)
    PIPELINE="$PIPELINE_DIR/assets_gen/gen_motion"
    ;;
  gen_audio)
    PIPELINE="$PIPELINE_DIR/assets_gen/gen_audio"
    ;;
  gen_cg_video)
    PIPELINE="$PIPELINE_DIR/assets_gen/gen_cg_video"
    ;;
  gen_tpose_image)
    PIPELINE="$PIPELINE_DIR/assets_gen/gen_tpose_image"
    ;;
  *)
    echo "Subcomando desconhecido: $SUBCMD" >&2
    usage; exit 1 ;;
esac

if [[ ! -d "$PIPELINE" ]]; then
  echo "Erro: pipeline não encontrada em $PIPELINE" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUTPUT" 2>/dev/null || echo .)"
LOG="${OUTPUT%.glb}.log"
LOG="${LOG%.ply}.log"
LOG="${LOG%/}".log
[[ "$LOG" == *.log.log ]] && LOG="${LOG%.log}"

START=$(date +%s)
echo "[gamefactory.sh] subcommand=$SUBCMD prompt='$PROMPT' output=$OUTPUT engine=$ENGINE" | tee -a "$LOG"

# O GameFactory-3A espera que um Coding Agent leia a skill e execute os
# operadores. Aqui disparamos via Python usando o entry point da pipeline.
ARGS=(
  "$PIPELINE"
  --output "$OUTPUT"
  --engine "$ENGINE"
)
[[ -n "$PROMPT" ]] && ARGS+=(--prompt "$PROMPT")
[[ -n "$TYPE" ]] && ARGS+=(--type "$TYPE")

cd "$GAMEFACTORY_DIR"
python3 -m pipeline_runner "${ARGS[@]}" 2>&1 | tee -a "$LOG" || {
  echo "[gamefactory.sh] Aviso: pipeline_runner não encontrado." >&2
  echo "GameFactory-3A requer um Coding Agent (Codex/Claude Code/Gemini CLI)." >&2
  echo "Carregue agent_skills/setting_overview.md e peça ao agente para gerar '$PROMPT' em '$OUTPUT'." >&2
}

END=$(date +%s)
META="${OUTPUT%/*}/meta.json"
[[ "$OUTPUT" == *.* ]] || META="$OUTPUT/meta.json"
cat > "$META" <<EOF
{
  "tool": "gamefactory-3a",
  "subcommand": "$SUBCMD",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "prompt": "$PROMPT",
  "output": "$OUTPUT",
  "engine": "$ENGINE",
  "type": "$TYPE"
}
EOF

echo "[gamefactory.sh] Concluído em $((END - START))s"
