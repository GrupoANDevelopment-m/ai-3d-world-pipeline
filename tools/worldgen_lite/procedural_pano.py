"""
procedural_pano.py — Gerador de panoramas procedurais MELHORADO.

Não usa FLUX (gated). Gera panoramas equirectangulares bonitas baseadas em
keywords do prompt, com:
  - Sky gradient com variação de tempo do dia
  - Terreno procedural (mountains, hills, water)
  - Nuvens/sol/lua por random seed determinístico
  - Árvores/texturas por bioma
  - Noise variation pra depth estimator funcionar

Fallback usado por t2mesh.py quando HF_TOKEN não fornecido.
"""
from __future__ import annotations

import hashlib
import math
import random
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


# ============================================================================
# Biomas predefinidos com cores + padrões
# ============================================================================

BIOMES: Dict[str, Dict] = {
    "snow": {
        "sky_top": (200, 215, 235),
        "sky_horizon": (220, 225, 240),
        "ground": (235, 240, 245),
        "ground_dark": (180, 190, 200),
        "features": ["mountains"],
        "feature_color": (220, 230, 240),
        "feature_dark": (140, 150, 170),
    },
    "mountain": {
        "sky_top": (110, 145, 200),
        "sky_horizon": (170, 195, 225),
        "ground": (95, 110, 75),
        "ground_dark": (60, 75, 50),
        "features": ["mountains", "rocks"],
        "feature_color": (130, 120, 110),
        "feature_dark": (85, 75, 70),
    },
    "alpine": {
        "sky_top": (135, 175, 220),
        "sky_horizon": (200, 220, 240),
        "ground": (130, 130, 130),
        "ground_dark": (90, 90, 90),
        "features": ["mountains", "snow_peaks"],
        "feature_color": (220, 225, 230),
        "feature_dark": (180, 185, 195),
    },
    "desert": {
        "sky_top": (200, 220, 240),
        "sky_horizon": (250, 220, 170),
        "ground": (235, 200, 145),
        "ground_dark": (200, 160, 100),
        "features": ["dunes"],
        "feature_color": (240, 215, 165),
        "feature_dark": (210, 175, 120),
    },
    "forest": {
        "sky_top": (130, 170, 200),
        "sky_horizon": (170, 200, 200),
        "ground": (50, 90, 45),
        "ground_dark": (30, 60, 30),
        "features": ["trees", "bushes"],
        "feature_color": (35, 95, 45),
        "feature_dark": (25, 65, 35),
    },
    "jungle": {
        "sky_top": (140, 180, 180),
        "sky_horizon": (180, 200, 180),
        "ground": (40, 80, 35),
        "ground_dark": (25, 55, 25),
        "features": ["trees", "vines"],
        "feature_color": (30, 75, 35),
        "feature_dark": (20, 55, 30),
    },
    "city": {
        "sky_top": (45, 55, 75),
        "sky_horizon": (90, 100, 120),
        "ground": (50, 50, 55),
        "ground_dark": (30, 30, 35),
        "features": ["buildings", "windows"],
        "feature_color": (60, 65, 75),
        "feature_dark": (40, 45, 55),
    },
    "urban": {
        "sky_top": (45, 55, 75),
        "sky_horizon": (90, 100, 120),
        "ground": (50, 50, 55),
        "ground_dark": (30, 30, 35),
        "features": ["buildings", "windows"],
        "feature_color": (60, 65, 75),
        "feature_dark": (40, 45, 55),
    },
    "night": {
        "sky_top": (5, 10, 25),
        "sky_horizon": (15, 20, 45),
        "ground": (20, 20, 35),
        "ground_dark": (5, 5, 15),
        "features": ["stars", "moon"],
        "feature_color": (200, 200, 230),
        "feature_dark": (180, 180, 200),
    },
    "ocean": {
        "sky_top": (130, 180, 220),
        "sky_horizon": (180, 220, 240),
        "ground": (40, 90, 150),
        "ground_dark": (20, 60, 110),
        "features": ["waves"],
        "feature_color": (50, 110, 175),
        "feature_dark": (30, 80, 130),
    },
    "beach": {
        "sky_top": (140, 180, 220),
        "sky_horizon": (200, 225, 240),
        "ground": (230, 215, 175),
        "ground_dark": (200, 180, 140),
        "features": ["water", "palm_trees"],
        "feature_color": (50, 110, 175),
        "feature_dark": (40, 80, 130),
    },
    "sunset": {
        "sky_top": (110, 70, 130),
        "sky_horizon": (240, 130, 80),
        "ground": (180, 90, 50),
        "ground_dark": (130, 60, 30),
        "features": ["sun", "silhouette"],
        "feature_color": (255, 200, 100),
        "feature_dark": (220, 130, 50),
    },
    "dawn": {
        "sky_top": (90, 110, 150),
        "sky_horizon": (240, 180, 130),
        "ground": (160, 140, 110),
        "ground_dark": (110, 90, 70),
        "features": ["sun"],
        "feature_color": (255, 220, 140),
        "feature_dark": (220, 170, 100),
    },
    "dusk": {
        "sky_top": (60, 50, 90),
        "sky_horizon": (200, 130, 110),
        "ground": (130, 80, 70),
        "ground_dark": (80, 50, 40),
        "features": ["stars", "silhouette"],
        "feature_color": (240, 200, 140),
        "feature_dark": (180, 130, 80),
    },
    "default": {
        "sky_top": (135, 175, 215),
        "sky_horizon": (185, 200, 220),
        "ground": (95, 115, 85),
        "ground_dark": (60, 80, 50),
        "features": ["trees"],
        "feature_color": (75, 95, 65),
        "feature_dark": (50, 70, 45),
    },
}

# time of day influence (none stored as basin)
TIME_KEYWORDS = {
    "sunset": "sunset",
    "dawn": "dawn",
    "dusk": "dusk",
    "night": "night",
    "evening": "sunset",
    "morning": "dawn",
    "twilight": "dusk",
}

# ============================================================================
# Detection helpers
# ============================================================================

def detect_biome(prompt: str) -> str:
    """Detecta bioma dominante do prompt."""
    p = prompt.lower()
    for keyword in BIOMES:
        if keyword in p:
            return keyword
    # fallback chain
    if any(k in p for k in ["mountain", "peak", "alpine", "summit"]):
        return "mountain"
    if any(k in p for k in ["forest", "tree", "woods"]):
        return "forest"
    if any(k in p for k in ["desert", "sand", "dune"]):
        return "desert"
    if any(k in p for k in ["city", "urban", "building", "skyline"]):
        return "city"
    if any(k in p for k in ["ocean", "sea", "water", "wave"]):
        return "ocean"
    if any(k in p for k in ["beach", "tropical", "palm"]):
        return "beach"
    if any(k in p for k in ["snow", "ice", "frozen"]):
        return "snow"
    return "default"


def _seed_from_prompt(prompt: str) -> int:
    """Deterministic seed from prompt (mesma prompt = mesmo output)."""
    h = hashlib.md5(prompt.encode()).hexdigest()
    return int(h[:8], 16)


# ============================================================================
# Sky drawing
# ============================================================================

def draw_sky(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    biome: Dict,
    width: int,
    height: int,
    rng: random.Random,
    night_mode: bool = False,
) -> None:
    """Desenha céu com gradient + nuvens/sol/lua/estrelas."""
    sky_top = biome["sky_top"]
    sky_horizon = biome["sky_horizon"]
    horizon_y = int(height * 0.5)

    # vertical gradient (mais escuro no topo, claro no horizon)
    for y in range(horizon_y):
        t = y / horizon_y
        r = int(sky_top[0] * t + sky_horizon[0] * (1 - t) * 0.4 + sky_top[0] * 0.6)
        g = int(sky_top[1] * t + sky_horizon[1] * (1 - t) * 0.4 + sky_top[1] * 0.6)
        b = int(sky_top[2] * t + sky_horizon[2] * (1 - t) * 0.4 + sky_top[2] * 0.6)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # detecta night mode from sky color (luminance < 80)
    sky_top_lum = 0.299 * sky_top[0] + 0.587 * sky_top[1] + 0.114 * sky_top[2]
    is_night = night_mode or sky_top_lum < 80

    # Stars (night detection por cor do céu ou feature)
    if is_night or "stars" in biome.get("features", []):
        for _ in range(int(width * height * 0.002)):
            x = rng.randint(0, width - 1)
            y = rng.randint(0, horizon_y - 10)
            brightness = rng.randint(150, 255)
            img.putpixel((x, y), (brightness, brightness, brightness))

    # Sun / moon: sempre se céu claro, OU se feature sun/moon, OU night com moon
    has_celestial = (
        not is_night or
        "sun" in biome.get("features", []) or
        any(f in biome.get("features", []) for f in ["sun", "moon"])
    )
    if has_celestial:
        sun_x = rng.randint(width // 4, 3 * width // 4)
        sun_y = int(horizon_y * 0.7) if not is_night else rng.randint(int(horizon_y * 0.2), int(horizon_y * 0.6))
        sun_r = max(20, height // 15)
        feature_color = (240, 230, 220) if is_night else (255, 220, 100)  # moon = white
        # halo
        for r_factor in [3, 2.5, 2, 1.5, 1]:
            r = int(sun_r * r_factor)
            for dx in range(-r, r, 2):
                for dy in range(-r, r, 2):
                    if dx * dx + dy * dy <= r * r:
                        px, py = sun_x + dx, sun_y + dy
                        if 0 <= px < width and 0 <= py < horizon_y:
                            alpha = max(0, 1 - (dx * dx + dy * dy) / (r * r))
                            existing = img.getpixel((px, py))
                            blended = tuple(
                                int(existing[i] * (1 - alpha * 0.4) + feature_color[i] * alpha * 0.4)
                                for i in range(3)
                            )
                            img.putpixel((px, py), blended)
        # core sun/moon
        outline = (180, 180, 200) if is_night else (180, 140, 80)
        draw.ellipse(
            [sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r],
            fill=feature_color,
            outline=outline,
        )

    # Clouds (wisp style)
    if rng.random() < 0.7:
        for _ in range(rng.randint(3, 8)):
            cx = rng.randint(0, width)
            cy = rng.randint(int(horizon_y * 0.2), int(horizon_y * 0.7))
            cw = rng.randint(40, 120)
            ch = rng.randint(15, 30)
            cloud_color = (
                int(sky_horizon[0] + 20),
                int(sky_horizon[1] + 20),
                int(sky_horizon[2] + 15),
            )
            for dx in range(-cw, cw, 2):
                for dy in range(-ch, ch, 2):
                    d = math.sqrt((dx / cw) ** 2 + (dy / ch) ** 2)
                    if d < 1.0:
                        alpha = (1 - d) * 0.4
                        px, py = cx + dx, cy + dy
                        if 0 <= px < width and 0 <= py < horizon_y:
                            existing = img.getpixel((px, py))
                            blended = tuple(
                                int(existing[i] * (1 - alpha) + cloud_color[i] * alpha)
                                for i in range(3)
                            )
                            img.putpixel((px, py), blended)


# ============================================================================
# Terrain drawing
# ============================================================================

def draw_terrain(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    biome: Dict,
    width: int,
    height: int,
    rng: random.Random,
    night_mode: bool = False,
) -> None:
    """Desenha terreno: gradient + features (montanhas, dunas, prédios, etc)."""
    horizon_y = int(height * 0.5)
    ground = biome["ground"]
    ground_dark = biome["ground_dark"]
    features = list(biome.get("features", []))
    if night_mode and "buildings" in features and "stars" not in features:
        features.append("stars")

    # ground gradient (claro perto do horizon, escuro embaixo)
    for y in range(horizon_y, height):
        t = (y - horizon_y) / (height - horizon_y)
        # exponential darkening
        factor = 1 - t ** 1.5
        r = int(ground[0] * factor + ground_dark[0] * (1 - factor))
        g = int(ground[1] * factor + ground_dark[1] * (1 - factor))
        b = int(ground[2] * factor + ground_dark[2] * (1 - factor))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # features (montanhas, dunas, prédios, árvores)
    feature_color = biome.get("feature_color", ground_dark)
    feature_dark = biome.get("feature_dark", ground_dark)

    if "mountains" in features or "snow_peaks" in features:
        n_peaks = rng.randint(5, 12)
        for i in range(n_peaks):
            cx = (i + rng.uniform(0, 1)) * width // n_peaks + rng.randint(-50, 50)
            peak_h = rng.randint(int(height * 0.15), int(height * 0.40))
            peak_w = rng.randint(60, 200)
            base_y = horizon_y + rng.randint(-10, 30)
            peak_color = (
                int(feature_color[0] + rng.randint(-15, 15)),
                int(feature_color[1] + rng.randint(-15, 15)),
                int(feature_color[2] + rng.randint(-15, 15)),
            )
            # polygon: base left, peak, base right
            points = [
                (cx - peak_w, height),
                (cx - peak_w // 2, base_y + peak_h),
                (cx, base_y),
                (cx + peak_w // 2, base_y + peak_h),
                (cx + peak_w, height),
            ]
            draw.polygon(points, fill=peak_color, outline=feature_dark)

            # Snow cap if alpine/snow
            if "snow_peaks" in features or rng.random() < 0.4:
                snow_h = peak_h // 3
                snow_color = (240, 245, 250)
                snow_points = [
                    (cx - peak_w // 4, base_y + peak_h - snow_h),
                    (cx, base_y),
                    (cx + peak_w // 4, base_y + peak_h - snow_h),
                ]
                if snow_h > 10:
                    draw.polygon(snow_points, fill=snow_color)

    elif "dunes" in features:
        for i in range(rng.randint(6, 15)):
            cx = rng.randint(0, width)
            base_y = horizon_y + rng.randint(0, 50)
            dune_h = rng.randint(15, 60)
            dune_w = rng.randint(80, 200)
            # smooth curve via arc
            bbox = [cx - dune_w, base_y - dune_h, cx + dune_w, base_y + dune_h // 4]
            draw.arc(bbox, 180, 360, fill=feature_dark, width=3)
            # fill below the arc
            draw.rectangle(
                [cx - dune_w, base_y, cx + dune_w, base_y + dune_h // 4],
                fill=feature_color,
            )

    elif "buildings" in features:
        # dense city skyline
        n_buildings = rng.randint(20, 40)
        max_width = width // 2  # spread across
        bx = -rng.randint(0, 80)
        for _ in range(n_buildings):
            bw = rng.randint(30, 100)
            gap = rng.randint(2, 15)
            if bx > width:
                break
            bh = rng.randint(60, int(height * 0.55))
            by_actual = horizon_y + (height - horizon_y) - bh - 5
            color = (
                int(feature_color[0] + rng.randint(-15, 15)),
                int(feature_color[1] + rng.randint(-15, 15)),
                int(feature_color[2] + rng.randint(-15, 15)),
            )
            draw.rectangle([bx, by_actual, bx + bw, by_actual + bh], fill=color, outline=feature_dark)
            # windows se for noite
            if night_mode:
                for wy in range(by_actual + 5, by_actual + bh - 5, 8):
                    for wx in range(bx + 5, bx + bw - 5, 8):
                        if rng.random() < 0.5:
                            wcolor = (
                                rng.randint(220, 255),
                                rng.randint(200, 240),
                                rng.randint(80, 180),
                            )
                            draw.rectangle([wx, wy, wx + 4, wy + 4], fill=wcolor)
            bx += bw + gap

    elif "trees" in features:
        # distant tree line
        n_trees = rng.randint(15, 40)
        for _ in range(n_trees):
            tx = rng.randint(0, width)
            th = rng.randint(8, 25)
            tw = rng.randint(8, 20)
            ty = horizon_y + rng.randint(0, 30)
            # triangle
            draw.polygon(
                [(tx, ty + th), (tx - tw, ty), (tx + tw, ty)],
                fill=feature_color,
            )

    elif "water" in features:
        # water (smooth)
        for y in range(horizon_y + 20, height):
            t = (y - horizon_y - 20) / (height - horizon_y - 20)
            # ripple pattern
            ripple = int(8 * math.sin(y * 0.3))
            color = (
                int(feature_color[0] + ripple),
                int(feature_color[1] + ripple),
                int(feature_color[2] + ripple),
            )
            draw.line([(0, y), (width, y)], fill=color)

    # texture variation (small noise for depth estimator)
    pixels = np.array(img)
    noise = np.random.RandomState(rng.randint(0, 1 << 30)).randint(-12, 12, pixels.shape).astype(np.int16)
    pixels = np.clip(pixels.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img.paste(Image.fromarray(pixels))


# ============================================================================
# Main entry
# ============================================================================

def generate(
    prompt: str,
    width: int = 1024,
    height: int = 512,
) -> Image.Image:
    """
    Gera panorama equirectangular 2:1 baseada no prompt.

    Args:
        prompt: text description
        width: largura da panorama (recomendado múltiplo de 256)
        height: altura (recomendado width/2 = equirectangular)

    Returns:
        PIL Image RGB
    """
    biome_name = detect_biome(prompt)
    biome = BIOMES[biome_name].copy()
    original_features = list(biome["features"])

    # check time of day: aplica só cores do tempo do dia, mantém features do bioma
    p_lower = prompt.lower()
    time_of_day = None
    for kw, time_biome in TIME_KEYWORDS.items():
        if kw in p_lower:
            time_of_day = time_biome
            break

    if time_of_day and time_of_day in BIOMES:
        # usa cores do tempo do dia, mas mantém features do bioma
        tod_biome = BIOMES[time_of_day]
        biome["sky_top"] = tod_biome["sky_top"]
        biome["sky_horizon"] = tod_biome["sky_horizon"]
        biome["ground"] = tod_biome["ground"]
        biome["ground_dark"] = tod_biome["ground_dark"]
        biome_name = time_of_day + "_" + biome_name  # ex: "night_city"

    # seed determinístico
    seed = _seed_from_prompt(prompt + biome_name)
    rng = random.Random(seed)

    # cria imagem base
    img = Image.new("RGB", (width, height), biome["sky_top"])
    draw = ImageDraw.Draw(img)

    # detecta night mode (preserva buildings)
    night_mode = "night" in str(biome.get("sky_top", "")) or "night" in p_lower

    # sky + horizon + features
    draw_sky(img, draw, biome, width, height, rng, night_mode=night_mode)
    draw_terrain(img, draw, biome, width, height, rng, night_mode=night_mode)

    # small blur pra suavizar
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    return img


def save(prompt: str, output_path: str, width: int = 1024, height: int = 512) -> str:
    """Helper: gera e salva panorama."""
    img = generate(prompt, width, height)
    img.save(output_path, quality=92)
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python procedural_pano.py <prompt> <output.jpg> [height=512]")
        sys.exit(1)
    prompt = " ".join(sys.argv[1:-1])
    out = sys.argv[-1]
    save(prompt, out)
    print(f"✓ panorama '{prompt[:50]}...' → {out}")