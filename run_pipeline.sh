#!/bin/bash
set -e
WORKSPACE=/workspace
TOOLS=$WORKSPACE/tools
BLENDER="$TOOLS/blender-4.2.5-linux-x64/blender"
GODOT="$TOOLS/Godot_v4.3-stable_linux.x86_64"
BYCOB="$TOOLS/world/build/bin/test_terrain"
BYCOB_TREE="$TOOLS/world/build/bin/test_tree"
SCRIPT_PY="$WORKSPACE/ai-3d-world-pipeline/tools/python/asset_processor.py"
OUT="$WORKSPACE/ai-3d-world-pipeline/outputs/persistent"
mkdir -p "$OUT/bycob" "$OUT/final" "$OUT/godot_project/assets"

echo "===[1/4] Bycob: terrain + trees"
mkdir -p /tmp/bycob_run
(cd /tmp/bycob_run && $BYCOB 2>&1 | tail -3) || true
(cd /tmp/bycob_run && $BYCOB_TREE 2>&1 | tail -3) || true
cp /tmp/bycob_run/assets/terrain/terrain.obj "$OUT/bycob/" 2>&1 || echo "  ! no terrain"
cp /tmp/bycob_run/assets/terrain/terrain.png "$OUT/bycob/" 2>&1 || true
cp -r /tmp/bycob_run/assets/tree "$OUT/bycob/" 2>&1 || true
ls "$OUT/bycob/" | head -10

echo ""
echo "===[2/4] Blender: OBJ -> GLB com LODs"
mkdir -p /tmp/blender_run
cp "$OUT/bycob/terrain.obj" /tmp/blender_run/
"$BLENDER" --background --python "$SCRIPT_PY" -- \
    --input /tmp/blender_run/terrain.obj \
    --output "$OUT/final/terrain.glb" \
    --max-tris 50000 \
    --lod-levels 3 \
    --collider trimesh 2>&1 | tail -10
ls -la "$OUT/final/terrain.glb" 2>&1

echo ""
echo "===[3/4] Godot: carrega GLB como PackedScene"
mkdir -p "$OUT/godot_project/assets"
cp "$OUT/final/terrain.glb" "$OUT/godot_project/assets/"
cat > "$OUT/godot_project/project.godot" <<'GODOT_EOF'
config_version=5
[application]
config/name="Persistent 3D World"
run/main_scene="res://main.tscn"
[rendering]
renderer/rendering_method="gl_compatibility"
GODOT_EOF

cat > "$OUT/godot_project/test_load.gd" <<'GD_EOF'
@tool
extends SceneTree

func _init():
    var glb_path = "res://assets/terrain.glb"
    if not FileAccess.file_exists(glb_path):
        print("FAIL: GLB nao encontrado")
        quit(1)
        return
    var scene = load(glb_path)
    if scene == null:
        print("FAIL: load retornou null")
        quit(2)
        return
    print("OK GLB type=", scene.get_class())
    if scene is PackedScene:
        var inst = scene.instantiate()
        if inst:
            print("OK instanciado tipo=", inst.get_class())
            var c = _count(inst)
            print("OK total nos=", c)
    quit(0)

func _count(node):
    var n = 1
    for c in node.get_children():
        n += _count(c)
    return n
GD_EOF

(cd "$OUT/godot_project" && "$GODOT" --headless --import 2>&1 | tail -3 || true)
(cd "$OUT/godot_project" && "$GODOT" --headless --script test_load.gd 2>&1 | grep -E "^(OK|FAIL)")

echo ""
echo "===[4/4] Relatorio final"
ls -la "$OUT/bycob/" 2>&1 | head
ls -la "$OUT/final/" 2>&1
du -sh "$OUT"/*
