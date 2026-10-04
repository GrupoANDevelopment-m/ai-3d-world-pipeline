#!/bin/bash
# gamefactory_3a.sh — wrapper pra GameFactory-3A (gerador de assets AAA-like)
REPO_ROOT="/workspace/ai-3d-world-pipeline"
cd "$REPO_ROOT" || exit 1
exec python3 -m tools.gamefactory_3a.generate_game "$@"