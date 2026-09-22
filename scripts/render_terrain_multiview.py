"""Renderiza Bycob terrain.obj de N ângulos diferentes usando OpenCV."""
import numpy as np
from PIL import Image
import os

os.makedirs('/workspace/colmap_terrain_images', exist_ok=True)

# Lê o OBJ (vertices são 'v x y z')
vertices = []
faces = []
with open('/workspace/bycob_terrain.obj') as f:
    for line in f:
        if line.startswith('v '):
            parts = line.split()
            vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif line.startswith('f '):
            parts = line.split()[1:]
            face = [int(p.split('/')[0]) - 1 for p in parts]
            faces.append(face)

vertices = np.array(vertices, dtype=np.float32)
print(f"Vertices: {len(vertices)}, Faces: {len(faces)}")
print(f"Bounds: x={vertices[:,0].min():.2f}..{vertices[:,0].max():.2f}, "
      f"y={vertices[:,1].min():.2f}..{vertices[:,1].max():.2f}, "
      f"z={vertices[:,2].min():.2f}..{vertices[:,2].max():.2f}")

# Centraliza e normaliza
center = vertices.mean(axis=0)
vertices -= center
scale = 2.0 / max(vertices.max(axis=0) - vertices.min(axis=0))
vertices *= scale
print(f"After normalize: bounds {vertices.max(axis=0) - vertices.min(axis=0)}")

# Função de projeção
def project(v, K, R, t):
    p_cam = (R @ v + t)
    if p_cam[2] <= 0.001:
        return None, None
    p_img = K @ p_cam / p_cam[2]
    return p_img[:2], p_cam[2]

def render_view(R, t, W=800, H=600):
    fov = 50
    f = W / (2 * np.tan(np.radians(fov/2)))
    K = np.array([[f, 0, W/2], [0, f, H/2], [0, 0, 1]])

    img = np.zeros((H, W, 3), dtype=np.uint8)
    zbuf = np.full((H, W), np.inf)

    def render_tri(tri):
        proj_pts = []
        depths = []
        for vi in tri:
            p, d = project(vertices[vi], K, R, t)
            proj_pts.append(p)
            depths.append(d)
        if any(p is None for p in proj_pts):
            return
        avg_depth = sum(depths) / 3
        v0 = vertices[tri[1]] - vertices[tri[0]]
        v1 = vertices[tri[2]] - vertices[tri[0]]
        normal = np.cross(v0, v1)
        nlen = np.linalg.norm(normal)
        if nlen < 1e-9:
            return
        normal = normal / nlen
        cam_normal = R @ normal
        light_dir = np.array([0.3, 0.3, 0.9])
        light_dir = light_dir / np.linalg.norm(light_dir)
        diffuse = max(0.2, abs(np.dot(cam_normal, light_dir)))
        z_avg = (vertices[tri[0]][2] + vertices[tri[1]][2] + vertices[tri[2]][2]) / 3
        if z_avg < -0.3:
            base_col = (50, 80, 180)
        elif z_avg < 0.0:
            base_col = (200, 180, 120)
        elif z_avg < 0.2:
            base_col = (80, 160, 80)
        else:
            base_col = (140, 130, 110)
        col = tuple(int(c * diffuse) for c in base_col)
        pts_2d = [(int(p[0]), int(p[1])) for p in proj_pts]
        if not all(0 <= p[0] < W and 0 <= p[1] < H for p in pts_2d):
            return
        minx = max(0, min(p[0] for p in pts_2d))
        maxx = min(W-1, max(p[0] for p in pts_2d))
        miny = max(0, min(p[1] for p in pts_2d))
        maxy = min(H-1, max(p[1] for p in pts_2d))
        if minx > maxx or miny > maxy:
            return
        for y in range(miny, maxy+1):
            for x in range(minx, maxx+1):
                p1, p2, p3 = pts_2d
                d00 = (p2[0]-p1[0])*(p2[1]-p3[1]) - (p2[1]-p1[1])*(p2[0]-p3[0])
                if abs(d00) < 1:
                    continue
                d01 = (p2[0]-p1[0])*(p1[1]-y) - (p2[1]-p1[1])*(p1[0]-x)
                d02 = (p3[0]-p1[0])*(p1[1]-y) - (p3[1]-p1[1])*(p1[0]-x)
                u = d01 / d00
                v = d02 / d00
                w = 1 - u - v
                if u >= 0 and v >= 0 and w >= 0:
                    if avg_depth < zbuf[y, x]:
                        zbuf[y, x] = avg_depth
                        img[y, x] = col

    # Renderiza faces (com z-buffer)
    for face in faces:
        if len(face) > 3:
            for i in range(1, len(face)-1):
                face_tris = [face[0], face[i], face[i+1]]
                render_tri(face_tris)
        else:
            render_tri(face)

    noise = np.random.randint(-5, 5, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(img)

# Câmera orbita em torno do terreno
N_VIEWS = 16
RADIUS = 2.5
HEIGHT = 1.5
for k in range(N_VIEWS):
    angle = k * (2 * np.pi / N_VIEWS) + 0.1
    cam_pos = np.array([RADIUS * np.cos(angle), RADIUS * np.sin(angle), HEIGHT])
    target = np.array([0, 0, 0])
    forward = target - cam_pos
    forward /= np.linalg.norm(forward)
    up = np.array([0, 0, 1])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    R = np.stack([right, up, forward])
    t = -R @ cam_pos  # transforma ponto do mundo para camera

    img = render_view(R, t)
    img.save(f'/workspace/colmap_terrain_images/view_{k:02d}.jpg', quality=95)

print(f"OK {N_VIEWS} views do Bycob terrain geradas")
