"""
_render_blender.py — Script Blender invocado por render_preview.py.

Lê args via sys.argv depois de -- separador.
"""
import bpy
import sys
import math
import os
import mathutils

# args vêm via sys.argv (Blender injeta --background --python <script> -- ...)
# Encontrar args após o separador --
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

# parse args
input_path = None
output_path = None
width = 800
height = 600
camera_angle = 30
camera_elevation = 35
samples = 32
engine = 'BLENDER_EEVEE_NEXT'
distance = None
prompt = ""  # pra tintar materiais baseado em keywords

i = 0
while i < len(argv):
    a = argv[i]
    if a == "--input" and i+1 < len(argv):
        input_path = argv[i+1]
        i += 2
    elif a == "--output" and i+1 < len(argv):
        output_path = argv[i+1]
        i += 2
    elif a == "--width" and i+1 < len(argv):
        width = int(argv[i+1])
        i += 2
    elif a == "--height" and i+1 < len(argv):
        height = int(argv[i+1])
        i += 2
    elif a == "--camera-angle" and i+1 < len(argv):
        camera_angle = float(argv[i+1])
        i += 2
    elif a == "--camera-elevation" and i+1 < len(argv):
        camera_elevation = float(argv[i+1])
        i += 2
    elif a == "--samples" and i+1 < len(argv):
        samples = int(argv[i+1])
        i += 2
    elif a == "--engine" and i+1 < len(argv):
        engine = argv[i+1]
        i += 2
    elif a == "--distance" and i+1 < len(argv):
        distance = float(argv[i+1])
        i += 2
    elif a == "--prompt" and i+1 < len(argv):
        prompt = argv[i+1].lower()
        i += 2
    else:
        i += 1

if not input_path or not output_path:
    print("USAGE: --input X --output Y", file=sys.stderr)
    sys.exit(2)

print(f"[render_blender] input: {input_path}", flush=True)
print(f"[render_blender] output: {output_path}", flush=True)
print(f"[render_blender] size: {width}x{height}, samples={samples}, engine={engine}", flush=True)

# Limpa cena
bpy.ops.wm.read_factory_settings(use_empty=True)

# Importa mesh
ext_low = os.path.splitext(input_path)[1].lower()
print(f"[render_blender] importing {ext_low}...", flush=True)

if ext_low in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=input_path)
elif ext_low in (".obj",):
    # WT obj importer is built into 4.2
    bpy.ops.wm.obj_import(filepath=input_path)
elif ext_low == ".ply":
    bpy.ops.wm.ply_import(filepath=input_path)
elif ext_low == ".stl":
    bpy.ops.import_mesh.stl(filepath=input_path)
elif ext_low == ".fbx":
    bpy.ops.import_scene.fbx(filepath=input_path)
else:
    print(f"Format not supported: {ext_low}", file=sys.stderr)
    sys.exit(3)

# Encontra objeto importado
imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not imported:
    print("No mesh found in scene", file=sys.stderr)
    sys.exit(4)
target = imported[0]
print(f"[render_blender] imported: {target.name}, {len(target.data.vertices)} verts", flush=True)

# Origem no centro do bounding box
bpy.context.view_layer.objects.active = target
target.select_set(True)
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Bounds
bbox_corners = [mathutils.Vector(corner) for corner in target.bound_box]
world_bbox = [target.matrix_world @ corner for corner in bbox_corners]
min_co = mathutils.Vector((min(v.x for v in world_bbox),
                            min(v.y for v in world_bbox),
                            min(v.z for v in world_bbox)))
max_co = mathutils.Vector((max(v.x for v in world_bbox),
                            max(v.y for v in world_bbox),
                            max(v.z for v in world_bbox)))
center = (min_co + max_co) / 2
size = (max_co - min_co).length
print(f"[render_blender] bbox center: {center}, size: {size}", flush=True)

if distance is None:
    distance = size * 1.8

# Câmera em orbita
angle_rad = math.radians(camera_angle)
elev_rad = math.radians(camera_elevation)
cam_x = center.x + distance * math.cos(elev_rad) * math.sin(angle_rad)
cam_y = center.y + distance * math.cos(elev_rad) * math.cos(angle_rad)
cam_z = center.z + distance * math.sin(elev_rad)

bpy.ops.object.camera_add(location=(cam_x, cam_y, cam_z))
camera = bpy.context.active_object
camera.name = "PreviewCamera"

direction = center - camera.location
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

bpy.context.scene.camera = camera

# Aplica material colorido baseado em prompt
def _biome_color(p: str) -> tuple:
    """Mapeia keywords do prompt pra cor RGB do material principal."""
    if any(k in p for k in ["snow", "alpine", "ice"]):
        return (0.95, 0.97, 1.0, 1.0)
    if any(k in p for k in ["desert", "sand", "dune"]):
        return (0.85, 0.7, 0.45, 1.0)
    if any(k in p for k in ["forest", "jungle", "tree"]):
        return (0.35, 0.55, 0.3, 1.0)
    if any(k in p for k in ["city", "urban", "building"]):
        return (0.55, 0.55, 0.6, 1.0)
    if any(k in p for k in ["water", "ocean", "sea"]):
        return (0.2, 0.4, 0.7, 1.0)
    if any(k in p for k in ["night"]):
        return (0.3, 0.3, 0.45, 1.0)
    if any(k in p for k in ["medieval", "village", "castle"]):
        return (0.55, 0.45, 0.35, 1.0)  # earthy brown
    if any(k in p for k in ["mountain", "rock"]):
        return (0.5, 0.45, 0.4, 1.0)
    return (0.6, 0.6, 0.6, 1.0)  # gray


mat = bpy.data.materials.new(name="BiomeMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
bsdf = nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = _biome_color(prompt)
    bsdf.inputs["Roughness"].default_value = 0.7

# Se o mesh tem vertex colors, usa eles via Attribute node (sobrepõe base color)
has_vc = False
try:
    has_vc = bool(target.data.color_attributes)
except AttributeError:
    # Blender < 3.2 API
    has_vc = bool(target.data.vertex_colors)

if has_vc and bsdf:
    # usa Attribute node pra vertex colors
    attr_node = nodes.new("ShaderNodeVertexColor")
    attr_node.layer_name = "Col" if "Col" in [a.name for a in (target.data.color_attributes or [])] else ""
    links.new(attr_node.outputs["Color"], bsdf.inputs["Base Color"])
    print(f"[render_blender] using vertex colors from mesh", flush=True)

# atribui material ao objeto importado
target.data.materials.clear()
target.data.materials.append(mat)

# Sun + world
bpy.ops.object.light_add(type='SUN', location=(cam_x, cam_y, cam_z + 30))
sun = bpy.context.active_object
sun.data.energy = 3.0

# Cria/garante world existe
if bpy.context.scene.world is None:
    new_world = bpy.data.worlds.new("PreviewWorld")
    bpy.context.scene.world = new_world
world = bpy.context.scene.world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')

# Aplica cor do céu baseado em prompt
sky_color = (0.6, 0.75, 0.9, 1.0)  # default blue
if any(k in prompt for k in ["sunset", "dusk", "dawn"]):
    sky_color = (0.95, 0.55, 0.35, 1.0)
elif any(k in prompt for k in ["night"]):
    sky_color = (0.05, 0.05, 0.15, 1.0)
elif any(k in prompt for k in ["desert", "sand"]):
    sky_color = (0.85, 0.75, 0.5, 1.0)
elif any(k in prompt for k in ["forest", "jungle"]):
    sky_color = (0.4, 0.65, 0.5, 1.0)
elif any(k in prompt for k in ["snow", "alpine"]):
    sky_color = (0.85, 0.9, 0.95, 1.0)
elif any(k in prompt for k in ["ocean", "beach"]):
    sky_color = (0.5, 0.75, 0.95, 1.0)
elif any(k in prompt for k in ["city", "urban"]):
    sky_color = (0.4, 0.45, 0.55, 1.0)

if bg:
    bg.inputs[0].default_value = sky_color
    bg.inputs[1].default_value = 1.0

# Render settings
scene = bpy.context.scene
scene.render.engine = engine
scene.render.resolution_x = width
scene.render.resolution_y = height
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = output_path

if engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.eevee.taa_render_samples = samples
    except AttributeError:
        scene.cycles.samples = samples
elif engine == 'CYCLES':
    scene.cycles.samples = samples
    scene.cycles.device = 'CPU'

print(f"[render_blender] rendering...", flush=True)
bpy.ops.render.render(write_still=True)
print(f"[render_blender] DONE: {output_path}", flush=True)