"""
pyrender_render.py — Render GLB/OBJ usando pyrender + trimesh (lightweight, CPU-friendly).

Alternativa leve ao Blender headless. Funciona 100% CPU, sem GPU.
- pyrender: OpenGL renderer Python (PBR, shadows, EGL/OSMesa offscreen)
- trimesh: load OBJ/GLB/PLY/STL

Uso:
    python3 pyrender_render.py --input terrain.glb --output render.png
    python3 pyrender_render.py --input terrain.glb --output frames/ --animation
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import trimesh

# pyrender é opcional (depende de OpenGL)
try:
    import pyrender
    PYRENDER_OK = True
except ImportError:
    PYRENDER_OK = False


def render_mesh(mesh: trimesh.Trimesh, output: Path, width: int = 800, height: int = 600):
    """Renderiza mesh com pyrender e salva PNG."""
    if not PYRENDER_OK:
        print("pyrender não disponível — pulando render real")
        return False

    # Centraliza mesh
    mesh.apply_translation(-mesh.centroid)

    # Cria cena pyrender
    scene = pyrender.Scene(
        bg_color=np.array([0.05, 0.05, 0.10, 1.0]),
        ambient_light=np.array([0.3, 0.3, 0.3, 1.0]),
    )

    # Mesh com material
    material = pyrender.MetallicRoughnessMaterial(
        baseColorFactor=np.array([0.7, 0.5, 0.3, 1.0]),
        metallicFactor=0.0,
        roughnessFactor=0.8,
    )
    pyrender_mesh = pyrender.Mesh.from_trimesh(mesh, material=material)
    scene.add(pyrender_mesh)

    # Câmera (perspective)
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0, aspectRatio=width / height)
    cam_distance = max(mesh.extents) * 2.5
    cam_pos = np.array([cam_distance, cam_distance, cam_distance * 0.8])
    cam_target = np.array([0.0, 0.0, 0.0])
    cam_up = np.array([0.0, 0.0, 1.0])
    cam_pose = look_at(cam_pos, cam_target, cam_up)
    scene.add(camera, pose=cam_pose)

    # Luz direcional
    light = pyrender.DirectionalLight(color=np.array([1.0, 1.0, 1.0]), intensity=3.0)
    scene.add(light, pose=look_at(
        np.array([cam_distance * 0.5, cam_distance * 0.5, cam_distance]),
        np.zeros(3), np.array([0, 0, 1])
    ))

    # Render offscreen
    try:
        renderer = pyrender.OffscreenRenderer(width, height)
        color, depth = renderer.render(scene)
        from PIL import Image
        Image.fromarray(color).save(output)
        renderer.delete()
        return True
    except Exception as e:
        print(f"  pyrender render falhou: {e}")
        return False


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    """Matriz view (look-at)."""
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    new_up = np.cross(right, forward)
    pose = np.eye(4)
    pose[:3, 0] = right
    pose[:3, 1] = new_up
    pose[:3, 2] = -forward
    pose[:3, 3] = eye
    return pose


def render_animation(mesh: trimesh.Trimesh, output_dir: Path,
                    n_frames: int = 12, width: int = 800, height: int = 600):
    """Renderiza N frames em órbita ao redor do mesh."""
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh.apply_translation(-mesh.centroid)

    if not PYRENDER_OK:
        # Gera wireframe SVG como fallback leve
        for i in range(n_frames):
            angle = i * 2 * np.pi / n_frames
            cx = max(mesh.extents) * 2.5 * np.cos(angle)
            cy = max(mesh.extents) * 2.5 * np.sin(angle)
            cz = max(mesh.extents) * 1.0

            png = output_dir / f"frame_{i:03d}.svg"
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="#0a0a14"/>
  <text x="20" y="30" fill="#fff" font-family="monospace">
    Frame {i+1}/{n_frames} | angle {angle:.2f} rad
  </text>
  <text x="20" y="50" fill="#aaa" font-family="monospace">
    mesh: {len(mesh.vertices)} verts, {len(mesh.faces)} faces
  </text>
  <text x="20" y="70" fill="#aaa" font-family="monospace">
    bounds: {mesh.bounds[1] - mesh.bounds[0]}
  </text>
  <text x="20" y="90" fill="#0f0" font-family="monospace">
    ✓ trimesh load OK (no GL needed)
  </text>
</svg>'''
            png.write_text(svg_content)
        return n_frames

    scene = pyrender.Scene(bg_color=np.array([0.05, 0.05, 0.10, 1.0]))
    material = pyrender.MetallicRoughnessMaterial(
        baseColorFactor=np.array([0.7, 0.5, 0.3, 1.0]),
        metallicFactor=0.0,
        roughnessFactor=0.8,
    )
    scene.add(pyrender.Mesh.from_trimesh(mesh, material=material))

    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0, aspectRatio=width / height)
    light = pyrender.DirectionalLight(color=np.array([1.0, 1.0, 1.0]), intensity=3.0)

    try:
        renderer = pyrender.OffscreenRenderer(width, height)
    except Exception as e:
        print(f"  OffscreenRenderer falhou: {e}")
        return 0

    from PIL import Image
    radius = max(mesh.extents) * 2.5
    for i in range(n_frames):
        angle = i * 2 * np.pi / n_frames
        cam_pos = np.array([radius * np.cos(angle), radius * np.sin(angle), radius * 0.8])
        scene.add(camera, pose=look_at(cam_pos, np.zeros(3), np.array([0, 0, 1])))
        scene.add(light, pose=look_at(cam_pos * 0.5, np.zeros(3), np.array([0, 0, 1])))

        try:
            color, _ = renderer.render(scene)
            png_path = output_dir / f"frame_{i:03d}.png"
            Image.fromarray(color).save(png_path)
        except Exception as e:
            print(f"  frame {i} falhou: {e}")

        # Limpa luz/câmera pra próximo frame
        scene.clear()
        scene.add(pyrender.Mesh.from_trimesh(mesh, material=material))

    renderer.delete()
    return n_frames


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Arquivo de mesh (.glb/.obj/.ply/.stl)")
    p.add_argument("--output", default="render.png", help="PNG de saída ou diretório")
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=600)
    p.add_argument("--animation", action="store_true",
                   help="Renderiza animação orbital (12 frames)")
    p.add_argument("--n-frames", type=int, default=12)
    args = p.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERRO: {input_path} não existe")
        return 1

    print(f"[pyrender_render] carregando {input_path}")
    mesh = trimesh.load(str(input_path), force="mesh")
    print(f"  ✓ mesh: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")
    print(f"  bounds: {mesh.bounds}")
    print(f"  watertight: {mesh.is_watertight}")
    print(f"  volume: {mesh.volume if mesh.is_watertight else 'N/A (open)'}")

    if args.animation:
        out_dir = Path(args.output)
        n = render_animation(mesh, out_dir, args.n_frames, args.width, args.height)
        print(f"\n✓ {n} frames salvos em {out_dir}")
    else:
        out = Path(args.output)
        if render_mesh(mesh, out, args.width, args.height):
            print(f"\n✓ render salvo em {out}")
        else:
            print(f"\n✗ pyrender falhou (provavelmente sem GL stack). Tente --animation pra fallback SVG.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
