"""
cubiquity_demo.py — Gera 4 voxel worlds via Cubiquity e cria montage PNG.

Uso:
    python3 cubiquity_demo.py --output outputs/cubiquity_demo

Algoritmos Cubiquity:
  - checkerboard   (padrão tabuleiro)
  - fractal_noise  (perlin-like 3D)
  - menger_sponge  (fractal cube)
  - worley_noise   (cellular pattern)
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image


CUBIQUITY = "/workspace/tools/cubiquity/build/cubiquity"
ALGOS = ["menger_sponge", "worley_noise", "fractal_noise", "checkerboard"]


def run(cmd: list, timeout=300) -> int:
    print(f"[run] {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=False, timeout=timeout).returncode


def generate_world(algo: str, out_dir: Path, size: int = 128) -> Path:
    """Generate a voxel world and export to PNG slices."""
    out_dir.mkdir(parents=True, exist_ok=True)
    name = algo.replace("_", "")

    # 1) generate .dag file
    dag = out_dir / f"{name}.dag"
    rc = run([CUBIQUITY, "generate", "--size", str(size), algo, str(dag)])
    if rc != 0:
        print(f"  [err] generate failed for {algo}")
        return None

    # 2) export as PNG slices
    pngs_dir = out_dir / f"{name}_pngs"
    pngs_dir.mkdir(exist_ok=True)
    rc = run([CUBIQUITY, "export", "pngs", str(dag), str(pngs_dir)])
    if rc != 0:
        print(f"  [err] export failed for {algo}")
        return None

    # Return first PNG
    pngs = sorted(pngs_dir.glob("*.png"))
    if pngs:
        return pngs[0]
    return None


def make_montage(samples: list, output: Path):
    """Create 2x2 montage of first slice of each algo."""
    if not samples:
        return
    maxw = max(im.size[0] for _, im in samples)
    maxh = max(im.size[1] for _, im in samples)
    montage = Image.new("RGB", (maxw * 2, maxh * 2), "white")
    for i, (name, im) in enumerate(samples):
        x = (i % 2) * maxw
        y = (i // 2) * maxh
        montage.paste(im.convert("RGB"), (x, y))
    montage.save(output)
    print(f"[montage] saved to {output} ({montage.size})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--size", type=int, default=128, help="Voxel side length")
    args = p.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    samples = []
    for algo in ALGOS:
        print(f"\n=== {algo} ===")
        png = generate_world(algo, out, args.size)
        if png and png.exists():
            im = Image.open(png)
            print(f"  [ok] {algo}: {im.size} {im.mode}")
            samples.append((algo, im))

    # Make montage
    if samples:
        montage_path = out / "montage.png"
        make_montage(samples, montage_path)
        print(f"\n[done] {len(samples)}/{len(ALGOS)} worlds generated")
        print(f"[done] montage: {montage_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
