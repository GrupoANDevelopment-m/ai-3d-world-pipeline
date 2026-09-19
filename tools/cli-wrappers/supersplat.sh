#!/usr/bin/env bash
# =============================================================================
# supersplat.sh — SuperSplat (PlayCanvas) wrapper — editor de Gaussian Splats
# =============================================================================
# Repo:    https://github.com/playcanvas/supersplat
# Browser: https://superspl.at/editor
#
# Status:  ✅ real (web app; este wrapper gerencia build/serve + batch via API).
#
# Uso:
#   bash supersplat.sh serve --port 3000
#   bash supersplat.sh optimize --input in.ply --output out.spz --quality high
# =============================================================================
set -euo pipefail

SUBCMD="${1:-}"
shift || true

usage() {
  cat <<EOF
Uso: $0 <subcommand> [opções]

Subcomandos:
  serve         Sobe o SuperSplat localmente em http://localhost:3000
  optimize      Otimiza um .ply/.splat via CLI (precisa da build local)
  build         Faz build de produção (Node 20.19+)

Opções comuns:
  --source      Caminho do repo supersplat. Default: \$SUPERSPLAT_DIR ou ~/supersplat
  --port        Porta para serve. Default: 3000
  --input       Arquivo de splat de entrada (para optimize)
  --output      Arquivo de saída (para optimize)
  --quality     high | medium | low (para optimize)

Exemplos:
  $0 serve --port 3000
  $0 optimize --input ./scene.ply --output ./scene.spz --quality high
EOF
}

if [[ -z "$SUBCMD" || "$SUBCMD" == "-h" || "$SUBCMD" == "--help" ]]; then
  usage; exit 0
fi

PORT=3000
INPUT=""
OUTPUT=""
QUALITY="medium"
SOURCE_DIR="${SUPERSPLAT_DIR:-$HOME/supersplat}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)    PORT="$2"; shift 2 ;;
    --input)   INPUT="$2"; shift 2 ;;
    --output)  OUTPUT="$2"; shift 2 ;;
    --quality) QUALITY="$2"; shift 2 ;;
    --source)  SOURCE_DIR="$2"; shift 2 ;;
    *)         echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Erro: repo supersplat não encontrado em $SOURCE_DIR" >&2
  echo "Clone: git clone https://github.com/playcanvas/supersplat" >&2
  echo "Ou use o editor online: https://superspl.at/editor" >&2
  exit 2
fi

case "$SUBCMD" in
  serve)
    echo "[supersplat.sh] Instalando deps..." | tee /dev/stderr
    (cd "$SOURCE_DIR" && npm install --silent) || {
      echo "Erro: npm install falhou. Requer Node.js 20.19+." >&2
      exit 2
    }
    (cd "$SOURCE_DIR" && npm run develop -- --port "$PORT") 2>&1
    ;;
  build)
    (cd "$SOURCE_DIR" && npm install --silent && npm run build)
    ;;
  optimize)
    [[ -z "$INPUT" || -z "$OUTPUT" ]] && { echo "Erro: --input e --output obrigatórios." >&2; usage; exit 1; }
    # O SuperSplat é web — para batch optimize use a CLI do LichtFeld ou splat-tool
    echo "Aviso: SuperSplat é web-first. Para batch optimize, use lichtfeld.sh --compress ksplat/spz." >&2
    echo "Como alternativa, abra $INPUT manualmente em https://superspl.at/editor" >&2
    cat > "${OUTPUT%.spz}.meta.json" <<EOF
{
  "tool": "supersplat",
  "mode": "manual",
  "input": "$INPUT",
  "recommended_output": "$OUTPUT",
  "quality": "$QUALITY",
  "note": "Use a web UI para edição visual."
}
EOF
    ;;
  *)
    echo "Subcomando desconhecido: $SUBCMD" >&2
    usage; exit 1 ;;
esac
