"""
i2mesh.py — Image-to-Mesh (panorama → 3D mesh) sem GPU.

Adapta WorldGen para CPU-only:
  1. Carrega panorama equirectangular
  2. Estima depth via panorama_depth.py (CPU heuristic)
  3. Converte em point cloud
  4. Poisson reconstruction → mesh
  5. Exporta .ply + opcional .obj

Uso:
    python3 -m tools.worldgen_lite.i2mesh --input pano.jpg --output scene.ply

Argumentos:
    --input     caminho da panorama equirectangular (2:1 aspect ratio)
    --output    caminho do .ply de saída
    --obj       também exportar .obj
    --method    poisson | ball_pivoting | alpha_shape
    --downscale fator de redução (default 8)
    --far       distância máxima em metros (default 100)
    --near      distância mínima em metros (default 0.5)
"""
import argparse
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(
        description="Image (panorama) → 3D mesh sem GPU. WorldGen-Lite CPU.",
    )
    p.add_argument("--input", required=True, help="Panorama equirectangular (jpg/png)")
    p.add_argument("--output", required=True, help="Output .ply path")
    p.add_argument("--obj", help="Também exportar .obj")
    p.add_argument("--method", default="poisson",
                   choices=["poisson", "ball_pivoting", "alpha_shape"])
    p.add_argument("--downscale", type=int, default=8)
    p.add_argument("--far", type=float, default=100.0)
    p.add_argument("--near", type=float, default=0.5)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"ERRO: {inp} não existe")
        return 1

    out_ply = Path(args.output)
    out_ply.parent.mkdir(parents=True, exist_ok=True)
    out_obj = Path(args.obj) if args.obj else None

    if not args.quiet:
        print(f"[i2mesh] input: {inp}")
        print(f"[i2mesh] output: {out_ply}")
        print(f"[i2mesh] method: {args.method}, downscale: {args.downscale}")

    # Lazy imports (cv2/torch/etc podem ser pesados)
    from .panorama_depth import panorama_to_rgbd
    from .depth_to_mesh import rgbd_to_mesh

    # 1. RGBD
    rgb, depth = panorama_to_rgbd(
        str(inp),
        downscale=args.downscale,
        far_clip=args.far,
        near_clip=args.near,
    )
    if not args.quiet:
        print(f"[i2mesh] rgb: {rgb.shape}, depth: {depth.shape}, "
              f"range: [{depth.min():.2f}, {depth.max():.2f}] m")

    # 2. Mesh
    stats = rgbd_to_mesh(
        rgb, depth,
        output_ply=str(out_ply),
        output_obj=str(out_obj) if out_obj else None,
        method=args.method,
    )

    print(f"[i2mesh] OK: {stats['n_points']} points → {stats['n_triangles']} triangles")
    print(f"[i2mesh]   → {stats['output_ply']}")
    if out_obj:
        print(f"[i2mesh]   → {stats['output_obj']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())