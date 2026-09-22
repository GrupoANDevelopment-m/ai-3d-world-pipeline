"""Gera dataset sintético que COLMAP consegue matchear - usa checkerboards e textura."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import random

os.makedirs('/workspace/colmap_real_test/images', exist_ok=True)
random.seed(42)
np.random.seed(42)

def render_scene(cam_x, cam_y, cam_z, look_x=0, look_y=0, look_z=0.5, W=800, H=600):
    """Renderiza cena com checkerboards 3D - COLMAP ama checkerboards."""
    # Câmera olha para target
    forward = np.array([look_x - cam_x, look_y - cam_y, look_z - cam_z])
    forward /= np.linalg.norm(forward)
    up = np.array([0, 0, 1])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)

    # Projeção simples
    fov = 60
    f = W / (2 * np.tan(np.radians(fov/2)))
    K = np.array([[f, 0, W/2], [0, f, H/2], [0, 0, 1]])
    R = np.stack([right, up, forward])

    # 6 planos de checkerboard em ângulos diferentes
    planes = []
    # Plano chão
    for i in range(4):
        angle = i * np.pi / 2
        planes.append({
            'pos': np.array([3*np.cos(angle), 3*np.sin(angle), 0]),
            'normal': np.array([-np.cos(angle), -np.sin(angle), 0]),
            'size': 4.0,
            'color1': (200, 100, 100),
            'color2': (100, 100, 200),
        })
    # Plano parede fundo
    planes.append({
        'pos': np.array([0, 4, 1.5]),
        'normal': np.array([0, -1, 0]),
        'size': 4.0,
        'color1': (100, 200, 100),
        'color2': (200, 200, 100),
    })
    # Cubo central
    cube_verts = [
        np.array([-0.5, -0.5, 0]), np.array([0.5, -0.5, 0]),
        np.array([0.5, 0.5, 0]), np.array([-0.5, 0.5, 0]),
        np.array([-0.5, -0.5, 1.5]), np.array([0.5, -0.5, 1.5]),
        np.array([0.5, 0.5, 1.5]), np.array([-0.5, 0.5, 1.5]),
    ]
    cube_faces = [
        # (vertex indices, color, brightness)
        ([0,1,2,3], (220,220,220), 1.0),  # top - bright
        ([0,1,5,4], (150,150,200), 0.7),  # front
        ([1,2,6,5], (150,150,150), 0.6),  # right
        ([2,3,7,6], (120,120,120), 0.5),  # back
    ]

    img = Image.new('RGB', (W, H), (30, 30, 50))
    draw = ImageDraw.Draw(img)
    zbuf = np.full((H, W), np.inf)

    def project(p3d):
        p_cam = R @ p3d + np.array([cam_x, cam_y, cam_z])
        if p_cam[2] <= 0:
            return None, None
        p_img = K @ p_cam / p_cam[2]
        return p_img[:2], p_cam[2]

    # Renderiza planos (checkerboard)
    for plane in planes:
        center = plane['pos']
        size = plane['size']
        normal = plane['normal']
        # Constrói base ortonormal do plano
        if abs(normal[2]) < 0.99:
            u_dir = np.cross(normal, np.array([0,0,1]))
        else:
            u_dir = np.cross(normal, np.array([1,0,0]))
        u_dir = u_dir / np.linalg.norm(u_dir)
        v_dir = np.cross(normal, u_dir)
        v_dir = v_dir / np.linalg.norm(v_dir)

        # Gera pontos do plano
        N = 30
        for iu in range(-N, N+1):
            for iv in range(-N, N+1):
                # Limita a uma região do plano
                u_off = iu / N * size
                v_off = iv / N * size
                if u_off*u_off + v_off*v_off > size*size/4:
                    continue  # só desenha círculo
                p3d = center + u_off * u_dir + v_off * v_dir
                p_img, depth = project(p3d)
                if p_img is None:
                    continue
                px, py = int(p_img[0]), int(p_img[1])
                if 0 <= px < W and 0 <= py < H and depth < zbuf[py, px]:
                    zbuf[py, px] = depth
                    # Checkerboard pattern
                    check = ((iu + iv) % 2 == 0)
                    c1 = plane['color1']
                    c2 = plane['color2']
                    col = c1 if check else c2
                    # Lighting simples baseado na direção da câmera
                    light = max(0.3, 1 - depth/20)
                    col = tuple(int(c * light) for c in col)
                    # Quadrado grande (2x2 pixels)
                    draw.rectangle([px-1, py-1, px+1, py+1], fill=col)

    # Renderiza cubo (4 faces frontais)
    for verts_idx, base_color, bright in cube_faces:
        proj_pts = []
        depths = []
        for vi in verts_idx:
            p, d = project(cube_verts[vi])
            proj_pts.append(p)
            depths.append(d)
        if any(p is None for p in proj_pts):
            continue
        avg_depth = sum(depths) / len(depths)
        if avg_depth >= np.inf:
            continue
        # Cor com lighting
        col = tuple(int(c * bright) for c in base_color)
        pts_2d = [(int(p[0]), int(p[1])) for p in proj_pts]
        # Triangula a face
        draw.polygon(pts_2d, fill=col, outline=(0,0,0))
        # Atualiza zbuf (não perfeito mas ok)
        for px, py in pts_2d:
            if 0 <= px < W and 0 <= py < H:
                zbuf[py, px] = avg_depth

    # Adiciona features: pontos pretos nas bordas (artificial, mas COLMAP detecta)
    img_arr = np.array(img)
    noise = np.random.randint(-8, 8, img_arr.shape, dtype=np.int16)
    img_arr = np.clip(img_arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(img_arr)

# Câmera orbita em torno da cena
N_VIEWS = 16
RADIUS = 4.0
HEIGHT = 2.5
for k in range(N_VIEWS):
    angle = k * (2 * np.pi / N_VIEWS)
    cam_x = RADIUS * np.cos(angle)
    cam_y = RADIUS * np.sin(angle)
    cam_z = HEIGHT
    img = render_scene(cam_x, cam_y, cam_z, 0, 0, 0.5)
    img.save(f'/workspace/colmap_real_test/images/view_{k:02d}.jpg', quality=95)

print(f"OK {N_VIEWS} imagens realistas geradas")
