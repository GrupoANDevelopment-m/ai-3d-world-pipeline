"""
pano_mesh.py — Equirectangular panorama → mesh com VERTEX COLORS.

Versão melhorada do depth_to_mesh que aplica as cores da panorama
diretamente nos vértices do mesh, criando uma textura implícita.

Resultado: mesh 3D com cores baked nas vertices (visível como
"terrain painting" sem precisar de UV unwrap ou material setup).
"""
from __future__ import annotations

import numpy as np
import open3d as o3d
from PIL import Image

from .panorama_depth import panorama_to_rgbd


def equirect_to_colored_pointcloud(
    rgb: np.ndarray,
    depth: np.ndarray,
) -> o3d.geometry.PointCloud:
    """
    Converte panorama em point cloud com cores baked nas vertices.

    Cada ponto do point cloud recebe a cor RGB do pixel correspondente.
    """
    h, w = rgb.shape[:2]

    # ângulos
    theta = (np.arange(w) / w) * 2 * np.pi
    phi = (np.arange(h) / h) * np.pi
    theta_grid, phi_grid = np.meshgrid(theta, phi)

    # coordenadas cartesianas
    x = depth * np.sin(phi_grid) * np.sin(theta_grid)
    y = depth * np.cos(phi_grid)
    z = depth * np.sin(phi_grid) * np.cos(theta_grid)

    points = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    colors = rgb.reshape(-1, 3).astype(np.float64) / 255.0

    pc = o3d.geometry.PointCloud()
    pc.points = o3d.utility.Vector3dVector(points)
    pc.colors = o3d.utility.Vector3dVector(colors)
    return pc


def colored_pointcloud_to_mesh(
    pc: o3d.geometry.PointCloud,
    method: str = "poisson",
) -> o3d.geometry.TriangleMesh:
    """Converte point cloud colorido em mesh triangular preservando cores."""
    pc_clean = pc

    # normal estimation
    pc_clean.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamKNN(knn=30))
    pc_clean.orient_normals_consistent_tangent_plane(k=20)

    if method == "poisson":
        mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pc_clean, depth=9, width=0, scale=1.1, linear_fit=False
        )
        mesh.compute_vertex_normals()
    elif method == "ball_pivoting":
        distances = pc_clean.compute_nearest_neighbor_distance()
        avg_dist = np.mean(distances)
        radii = [avg_dist * r for r in [1, 2, 4, 8, 16, 32]]
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
            pc_clean, o3d.utility.DoubleVector(radii)
        )
    else:
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(pc_clean, alpha=0.5)

    # preserva vertex colors (que vêm do point cloud)
    if not pc_clean.has_colors():
        mesh.vertex_colors = o3d.utility.Vector3dVector([])

    # limpeza
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    return mesh


def pano_to_colored_mesh(
    rgb: np.ndarray,
    depth: np.ndarray,
    output_ply: str,
    output_obj: str | None = None,
    method: str = "poisson",
) -> dict:
    """
    Pipeline: panorama RGB+depth → mesh com cores baked.
    """
    pc = equirect_to_colored_pointcloud(rgb, depth)
    n_points = len(pc.points)
    mesh = colored_pointcloud_to_mesh(pc, method=method)
    n_triangles = len(mesh.triangles)

    o3d.io.write_triangle_mesh(output_ply, mesh)
    if output_obj:
        o3d.io.write_triangle_mesh(output_obj, mesh)

    return {
        "n_points": n_points,
        "n_triangles": n_triangles,
        "output_ply": output_ply,
        "output_obj": output_obj,
        "has_colors": mesh.has_vertex_colors(),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python pano_mesh.py <panorama.jpg> <output.ply> [output.obj]")
        sys.exit(1)
    rgb, depth = panorama_to_rgbd(sys.argv[1])
    out_obj = sys.argv[3] if len(sys.argv) > 3 else None
    stats = pano_to_colored_mesh(rgb, depth, sys.argv[2], out_obj)
    print(f"✓ mesh colorido: {stats['n_points']} pts → {stats['n_triangles']} tris")
    print(f"  colors: {stats['has_colors']}")
    print(f"  → {stats['output_ply']}")
    if out_obj:
        print(f"  → {stats['output_obj']}")