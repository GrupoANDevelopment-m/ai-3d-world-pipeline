#!/usr/bin/env bash
# =============================================================================
# run_pipeline.sh — Executa o pipeline completo end-to-end
# Uso: bash /workspace/ai-3d-world-pipeline/run_pipeline.sh
# =============================================================================
set -e
TOOLS=/workspace/tools
OUT=${1:-/workspace/ai-3d-world-pipeline/outputs/demo_run}
PIPELINE=/workspace/ai-3d-world-pipeline
mkdir -p "$OUT"/{bycob,final,godot}

echo "=== [1/4] Bycob C++ terrain ==="
mkdir -p /tmp/bycob_run
(cd /tmp/bycob_run && $TOOLS/world/build/bin/test_terrain 2>&1 | tail -1) || true
(cd /tmp/bycob_run && $TOOLS/world/build/bin/test_tree 2>&1 | tail -1) || true
cp /tmp/bycob_run/assets/terrain/terrain.obj "$OUT/bycob/" 2>&1 || true
cp -r /tmp/bycob_run/assets/tree "$OUT/bycob/" 2>&1 || true

echo "=== [2/4] Blender OBJ -> GLB ==="
$TOOLS/blender-4.2.5-linux-x64/blender --background --python $PIPELINE/tools/python/asset_processor.py -- \
    --input "$OUT/bycob/terrain.obj" --output "$OUT/final/terrain.glb" \
    --max-tris 50000 --lod-levels 3 --collider trimesh 2>&1 | tail -2

echo "=== [3/4] validate GLB ==="
python3 $PIPELINE/tools/python/gltf_validator.py --input "$OUT/final/terrain.glb" 2>&1

echo "=== [4/4] OpenSplat CPU 3DGS smoke ==="
timeout 5 $TOOLS/OpenSplat/build/simple_trainer 2>&1 | head -5

echo ""
ls -la "$OUT"/bycob/terrain.obj "$OUT"/final/terrain.glb
