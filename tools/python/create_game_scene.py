"""
create_game_scene.py — Cria cena Godot 4 jogável a partir de GLB do Bycob.
"""
import argparse
import shutil
import sys
from pathlib import Path


# main.tscn usa ext_resource paths (não UIDs) pra funcionar em cold-load
MAIN_TSCN = """[gd_scene load_steps=4 format=3]

[ext_resource type="PackedScene" path="res://assets/world.glb" id="1_world"]
[ext_resource type="Script" path="res://scripts/player.gd" id="2_player"]

[sub_resource type="BoxShape3D" id="BoxShape3D_player"]
size = Vector3(0.6, 1.8, 0.6)

[sub_resource type="Environment" id="Environment_main"]
background_mode = 1
sky_color = Color(0.4, 0.6, 0.9, 1)
ambient_light_source = 2
ambient_light_color = Color(0.7, 0.8, 1, 1)
ambient_light_energy = 0.5
fog_enabled = true
fog_density = 0.005

[node name="Main" type="Node3D"]

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("Environment_main")

[node name="Sun" type="DirectionalLight3D" parent="."]
transform = Transform3D(0.7, -0.5, 0.5, 0, 0.7, 0.7, -0.7, -0.5, 0.5, 0, 30, 0)
shadow_enabled = true
light_energy = 1.2

[node name="Terrain" type="Node3D" parent="."]

[node name="TerrainInstance" parent="Terrain" instance=ExtResource("1_world")]
transform = Transform3D(10, 0, 0, 0, 10, 0, 0, 0, 10, 0, 0, 0)

[node name="Player" type="CharacterBody3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 8, 0)
script = ExtResource("2_player")

[node name="CollisionShape3D" type="CollisionShape3D" parent="Player"]
shape = SubResource("BoxShape3D_player")

[node name="Camera3D" type="Camera3D" parent="Player"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.6, 0)
current = true
fov = 75.0
"""

PLAYER_GD = '''extends CharacterBody3D

@export var speed: float = 8.0
@export var jump_velocity: float = 5.0
@export var mouse_sensitivity: float = 0.003

@onready var camera: Camera3D = $Camera3D

func _ready() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseMotion:
        rotate_y(-event.relative.x * mouse_sensitivity)
        camera.rotate_x(-event.relative.y * mouse_sensitivity)
        camera.rotation.x = clamp(camera.rotation.x, -PI/2, PI/2)

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y -= 12.0 * delta

    if Input.is_action_just_pressed("ui_accept") and is_on_floor():
        velocity.y = jump_velocity

    var input_dir := Input.get_vector("move_left", "move_right", "move_up", "move_down")
    var direction := (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
    if direction:
        velocity.x = direction.x * speed
        velocity.z = direction.z * speed
    else:
        velocity.x = move_toward(velocity.x, 0, speed)
        velocity.z = move_toward(velocity.z, 0, speed)

    move_and_slide()
'''

PROJECT_GODOT = """config_version=5

[application]
config/name="Generated World"
run/main_scene="res://scenes/main.tscn"

[input]
move_left={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":65,"key_label":0,"unicode":97,"location":0,"echo":false,"script":null)
]
}
move_right={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":68,"key_label":0,"unicode":100,"location":0,"echo":false,"script":null)
]
}
move_up={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":87,"key_label":0,"unicode":119,"location":0,"echo":false,"script":null)
]
}
move_down={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":83,"key_label":0,"unicode":115,"location":0,"echo":false,"script":null)
]
}

[rendering]
renderer/rendering_method="gl_compatibility"
environment/defaults/default_clear_color=Color(0.4, 0.6, 0.9, 1)
"""


def create_godot_project(glb_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    scripts_dir = output_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    scenes_dir = output_dir / "scenes"
    scenes_dir.mkdir(exist_ok=True)

    # Copy GLB
    target_glb = assets_dir / "world.glb"
    shutil.copy2(glb_path, target_glb)
    print(f"  [assets] {target_glb.name} ({target_glb.stat().st_size:,} bytes)")

    (output_dir / "project.godot").write_text(PROJECT_GODOT)
    print(f"  [config] project.godot (WASD inputs)")

    (scripts_dir / "player.gd").write_text(PLAYER_GD)
    print(f"  [scripts] player.gd (CharacterBody3D + Camera + WASD + mouse look)")

    (scenes_dir / "main.tscn").write_text(MAIN_TSCN)
    print(f"  [scenes] main.tscn (terrain + sun + player + camera)")

    return output_dir


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--glb", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    glb = Path(args.glb)
    out = Path(args.output)

    if not glb.exists():
        print(f"ERRO: {glb} não existe")
        return 1

    print(f"[create_game_scene] glb: {glb} ({glb.stat().st_size:,} bytes)")
    print(f"[create_game_scene] output: {out}")
    create_godot_project(glb, out)
    print(f"\n✓ Projeto Godot criado em: {out}")
    print(f"  Para rodar: godot --path {out}")
    print(f"  Controles: WASD = mover, Space = pular, Mouse = olhar, Esc = liberar cursor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
