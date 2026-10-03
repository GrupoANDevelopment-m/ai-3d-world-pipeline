"""
depth_to_mesh.py — Converte RGBD panorama em mesh 3D.

Adapta parte do WorldGen (worldgen.py: convert_rgbd2mesh_panorama) pra
versão CPU-only usando open3d + numpy.

Pipeline:
  1. Panorama equirectangular → projection 3D usando coordenadas esféricas
  2. Pontos RGBD viram point cloud
  3. Point cloud → mesh via Poisson reconstruction (CPU)
  4. Salva .ply + .obj
"""
from __future__ import annotations

import numpy as np
import open3d as o3d
from PIL import Image


def equirect_to_pointcloud(
    rgb: np.ndarray,
    depth: np.ndarray,
    fov_deg: float = 90.0,
) -> o3d.geometry.PointCloud:
    """
    Converte panorama equirectangular RGB+depth em point cloud.

    Args:
        rgb: H x W x 3 uint8
        depth: H x W float32 (metros)
        fov_deg: FOV vertical (default 90 = half sphere)

    Returns:
        open3d PointCloud
    """
    h, w = rgb.shape[:2]

    # ângulos: theta (azimuth) = longitude, phi (polar) = latitude
    # equirectangular: x=col → theta=0..2π, y=row → phi=0..π
    theta = (np.arange(w) / w) * 2 * np.pi        # 0 to 2π
    phi = (np.arange(h) / h) * np.pi              # 0 to π

    # meshgrid
    theta_grid, phi_grid = np.meshgrid(theta, phi)

    # converte pra cartesiano (esfera unitária * depth)
    x = depth * np.sin(phi_grid) * np.sin(theta_grid)
    y = depth * np.cos(phi_grid)                  # up
    z = depth * np.sin(phi_grid) * np.cos(theta_grid)

    points = np.stack([x, y, z], axis=-1).reshape(-1, 3)

    # RGB: redimensiona se necessário
    colors = rgb.reshape(-1, 3).astype(np.float64) / 255.0

    pc = o3d.geometry.PointCloud()
    pc.points = o3d.utility.Vector3dVector(points)
    pc.colors = o3d.utility.Vector3dVector(colors)
    return pc


def pointcloud_to_mesh(
    pc: o3d.geometry.PointCloud,
    method: str = "poisson",
    density_quantile: float = 0.05,
) -> o3d.geometry.TriangleMesh:
    """
    Converte point cloud em mesh triangular.

    Args:
        pc: point cloud
        method: "poisson" (recomendado) | "ball_pivoting" | "alpha_shape"
        density_quantile: corta pontos abaixo desse quantil (outliers)
    """
    # remove outliers
    if density_quantile > 0:
        densities = np.asarray(pc.compute_point_cloud_distance(
            pc.voxel_down_sample(voxel_size=0.05)
        ))
        densities = densities / (densities.max() + 1e-6)
        keep = densities < density_quantile
        pc_clean = pc.select_by_index(np.where(keep)[0])
    else:
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
    elif method == "alpha_shape":
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(pc_clean, alpha=0.5)
    else:
        raise ValueError(f"method '{method}' não reconhecido")

    # limpa mesh
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    return mesh


def rgbd_to_mesh(
    rgb: np.ndarray,
    depth: np.ndarray,
    output_ply: str,
    output_obj: str | None = None,
    method: str = "poisson",
) -> dict:
    """
    Pipeline completo: RGBD panorama → mesh (.ply e opcional .obj).

    Returns:
        dict com stats (n_points, n_triangles)
    """
    pc = equirect_to_pointcloud(rgb, depth)
    n_points = len(pc.points)
    mesh = pointcloud_to_mesh(pc, method=method)
    n_triangles = len(mesh.triangles)

    o3d.io.write_triangle_mesh(output_ply, mesh)
    if output_obj:
        # open3d exporta obj simples
        o3d.io.write_triangle_mesh(output_obj, mesh)

    return {
        "n_points": n_points,
        "n_triangles": n_triangles,
        "output_ply": output_ply,
        "output_obj": output_obj,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python depth_to_mesh.py <panorama.jpg> <output.ply> [output.obj]")
        sys.exit(1)
    from .panorama_depth import panorama_to_rgbd
    rgb, depth = panorama_to_rgbd(sys.argv[1])
    out_obj = sys.argv[3] if len(sys.argv) > 3 else None
    stats = rgbd_to_mesh(rgb, depth, sys.argv[2], out_obj)
    print(f"✓ mesh gerado: {stats['n_points']} points → {stats['n_triangles']} triangles")
    print(f"  → {stats['output_ply']}")
    if out_obj:
        print(f"  → {stats['output_obj']}")