#!/bin/bash
# worldgen_lite_i2mesh.sh — WorldGen-Lite image→mesh (CPU-only)
# Adapta https://github.com/ZiYang-xie/WorldGen pra hardware limitado.
# Skip FLUX.1-dev (gated), usa panorama input + depth heuristic + Poisson mesh.
REPO_ROOT="/workspace/ai-3d-world-pipeline"
cd "$REPO_ROOT" || exit 1
exec python3 -m tools.worldgen_lite.i2mesh "$@"