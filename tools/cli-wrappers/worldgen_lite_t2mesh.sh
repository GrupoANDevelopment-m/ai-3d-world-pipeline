#!/bin/bash
# worldgen_lite_t2mesh.sh — WorldGen-Lite text→mesh (CPU-friendly).
# Se HF_TOKEN fornecido: usa FLUX.1-dev real (gated).
# Senão: usa procedural panorama fallback.
REPO_ROOT="/workspace/ai-3d-world-pipeline"
cd "$REPO_ROOT" || exit 1
exec python3 -m tools.worldgen_lite.t2mesh "$@"