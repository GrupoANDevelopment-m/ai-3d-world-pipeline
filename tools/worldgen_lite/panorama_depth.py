"""
panorama_depth.py — Estimativa de profundidade leve para panoramas.

Adapta a parte do WorldGen (pano_depth.py) que usa DA-2. Como DA-2
requer GPU pesado, usamos um approach CPU-friendly baseado em:

  - Variação de luminância (sky/ground detection)
  - Gradientes verticais (panoramas: top = sky, bottom = ground)
  - Heurística de saturação (sky saturado, foreground detalhado)
  - Inpainting de buracos via Gaussian smoothing

Output: depth map 2D (H/8 × W) com float [0,1] representando distância.

Para o usuário ter um substituto ao DA-2 sem GPU:
  - depth = f(luminance, vertical_position, saturation)
  - calibrado empiricamente pra panoramas equirectangular 2:1
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def _rgb_to_lum(img: np.ndarray) -> np.ndarray:
    """Converte RGB pra luminância Y."""
    return 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]


def estimate_depth_simple(
    img: np.ndarray,
    downscale: int = 8,
    sky_threshold: float = 0.85,
) -> np.ndarray:
    """
    Estima depth map de panorama equirectangular 2:1 usando heurística:
      - luminância alta no topo + saturação baixa = sky (longe)
      - luminância baixa + textura = foreground (perto)
      - vertical position: top→down, distância crescente

    Args:
        img: HxWx3 uint8 panorama
        downscale: factor de redução (8 = H/8 × W)
        sky_threshold: luminância mínima pra considerar sky

    Returns:
        depth: (H/downscale) × W float32 [0,1], 0=perto, 1=longe
    """
    h, w = img.shape[:2]
    # Reduz resolução
    img_small = img[::downscale, ::1]   # H/downscale, W, 3
    lum = _rgb_to_lum(img_small)        # H/downscale, W
    sat = img_small.max(axis=-1).astype(np.float32) - img_small.min(axis=-1).astype(np.float32)
    sat = sat / 255.0
    lum_norm = lum / 255.0

    # Vertical position: 0 (top) → 1 (bottom)
    v_pos = np.linspace(0, 1, img_small.shape[0])[:, None].repeat(w, axis=1)

    # Heurística 1: luminância + sky threshold = sky detection
    is_sky = (lum_norm > sky_threshold) & (sat < 0.2)

    # Heurística 2: gradiente vertical = ceiling (topo) vs floor (base)
    # top sky = longe
    # bottom floor = perto
    base_depth = v_pos * 0.5 + 0.5  # topo=0.5, bottom=1.0

    # Heurística 3: variation local = texturas (perto)
    # calcula std local via diferença de pixels vizinhos
    local_var = np.zeros_like(lum_norm)
    local_var[1:-1, 1:-1] = np.abs(
        lum_norm[1:-1, 1:-1] - lum_norm[:-2, :-2]
    ) + np.abs(
        lum_norm[1:-1, 1:-1] - lum_norm[2:, 2:]
    )

    # Ajusta: sky → longe (1.0), textura alta → perto (0.3)
    depth = base_depth.copy()
    depth[is_sky] = np.maximum(depth[is_sky], 0.95)
    depth = depth - 0.3 * local_var / (local_var.max() + 1e-6)
    depth = np.clip(depth, 0.1, 1.0)

    # Suaviza com Gaussian simples (inpaint buracos)
    from scipy.ndimage import gaussian_filter
    depth = gaussian_filter(depth, sigma=2.0)

    return depth.astype(np.float32)


def panorama_to_rgbd(
    img_path: str,
    downscale: int = 8,
    far_clip: float = 100.0,
    near_clip: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Carrega panorama e retorna (rgb, depth) prontos pra reconstrução.

    rgb: H x W x 3 uint8 (resolução reduzida)
    depth: H x W float32 em metros (far_clip = longe, near_clip = perto)
    """
    pil_img = Image.open(img_path).convert("RGB")
    img_arr = np.asarray(pil_img)
    # Reduz mid? Reduz mid? Reduz resolução
    img_small = img_arr[::downscale, ::1]
    depth_norm = estimate_depth_simple(img_small, downscale=1)  # já está pequeno

    # Converte depth normalizado [0,1] → metros
    depth_m = near_clip + depth_norm * (far_clip - near_clip)

    return img_small, depth_m


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python panorama_depth.py <panorama.jpg>")
        sys.exit(1)
    rgb, depth = panorama_to_rgbd(sys.argv[1])
    print(f"rgb shape: {rgb.shape}")
    print(f"depth shape: {depth.shape}, range: [{depth.min():.2f}, {depth.max():.2f}]")