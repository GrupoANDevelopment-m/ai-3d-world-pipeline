"""
GameFactory-3A — Geração de assets prontos pra games.

Adapta o conceito "GameFactory-3A" (text-to-game-assets) usando o que temos:
  - worldgen_lite_t2mesh → panorama → mesh (.ply/.obj)
  - cubiquity_generate → voxel world (.dag + PNG slices)
  - bycob_world → procedural terrain (mesh + vegetation)
  - blender_process → OBJ→GLB com LODs

Pipeline "A3A" = 3A-grade assets (pipeline "AAA-like" para indie games):

  text prompt
       ↓
  [1] WorldGen-Lite → terrain/environment mesh
       ↓
  [2] Cubiquity OR Bycob → assets complementares (voxel world OU tree instances)
       ↓
  [3] Blender → LODs + GLB
       ↓
  [4] gltf_validator → check
       ↓
  [5] godot_build_scene → game project (WASD player + camera + scene)

Output: projeto Godot 4 completo pronto pra abrir e jogar.
"""
__version__ = "0.1.0"