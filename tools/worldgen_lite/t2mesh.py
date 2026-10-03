"""
t2mesh.py — Text-to-Mesh pipeline (text → panoramic image → 3D mesh).

Adapta WorldGen (pano_gen.py + worldgen.py) pra CPU-only / acessível:

  text prompt
       │
       ▼
  [1] panoramic image
       │
       ├─ if HF_TOKEN + FLUX.1-dev gated accepted → usa FLUX (melhor qualidade)
       ├─ else if user tem local Stable Diffusion / SD via HF diffusers
       └─ else → usa paisagem procedural (gradiente + nuvens) ou aborta

       │
       ▼
  [2] panorama_depth.py → depth
       │
       ▼
  [3] depth_to_mesh.py → mesh

Uso:
    # Com FLUX.1-dev via HF token (gated)
    HF_TOKEN="hf_xxxxx" python3 -m tools.worldgen_lite.t2mesh \\
        --prompt "A beautiful landscape with mountains" --output scene.ply

    # Sem FLUX (fallback procedural skybox + mountains)
    python3 -m tools.worldgen_lite.t2mesh \\
        --prompt "Any text" --output scene.ply --fallback-procedural
"""
import argparse
import sys
from pathlib import Path


def generate_panorama_procedural(
    prompt: str,
    width: int = 1024,
    height: int = 512,
) -> str:
    """
    Fallback procedural sem FLUX. Gera panorama colorido baseado em palavras do prompt.

    Heurística simples:
      - palavras "sky", "blue" → céu azul
      - palavras "mountain", "snow" → montanhas brancas
      - palavras "desert", "sand" → deserto amarelo
      - palavras "forest", "green" → floresta verde
      - palavras "city", "night" → cidade noturna
      - default → gradient sunset
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter

    prompt_l = prompt.lower()
    if any(k in prompt_l for k in ["mountain", "snow", "alpine"]):
        sky_color = (170, 200, 230)
        ground_color = (200, 200, 210)
    elif any(k in prompt_l for k in ["desert", "sand", "dune"]):
        sky_color = (250, 200, 150)
        ground_color = (220, 180, 120)
    elif any(k in prompt_l for k in ["forest", "jungle", "green"]):
        sky_color = (180, 220, 200)
        ground_color = (80, 120, 60)
    elif any(k in prompt_l for k in ["city", "urban", "night"]):
        sky_color = (20, 25, 50)
        ground_color = (40, 40, 60)
    elif any(k in prompt_l for k in ["ocean", "sea", "water"]):
        sky_color = (180, 220, 240)
        ground_color = (40, 100, 160)
    elif any(k in prompt_l for k in ["sunset", "dawn", "dusk"]):
        sky_color = (240, 130, 80)
        ground_color = (180, 90, 50)
    else:
        # default: sky genérico
        sky_color = (135, 180, 220)
        ground_color = (90, 110, 80)

    # Cria panorama: gradient horizontal (sky em cima) + terreno embaixo
    img = Image.new("RGB", (width, height), sky_color)
    draw = ImageDraw.Draw(img)

    # horizon line no meio
    horizon_y = height // 2

    # gradient no sky (top mais claro, horizon mais saturado)
    for y in range(horizon_y):
        t = y / horizon_y
        r = int(sky_color[0] * (1 - t * 0.2) + sky_color[0] * t * 0.2)
        g = int(sky_color[1] * (1 - t * 0.15) + sky_color[1] * t * 0.15)
        b = int(sky_color[2] * (1 - t * 0.1))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # ground gradient
    for y in range(horizon_y, height):
        t = (y - horizon_y) / (height - horizon_y)
        # + escuro embaixo
        rr = int(g_r := int(ground_color[0] * (1 - t * 0.3)))
        gg = int(g_g := int(ground_color[1] * (1 - t * 0.3)))
        bb = int(g_b := int(ground_color[2] * (1 - t * 0.4)))
        draw.line([(0, y), (width, y)], fill=(rr, gg, bb))

    # Adiciona noise/variation pra depth estimator pegar texturas
    import random
    rng = random.Random(hash(prompt) & 0xffffffff)
    pixels = np.array(img)
    # noise sutil
    noise_mask = np.random.RandomState(rng.randint(0, 1<<30)).randint(-15, 15, pixels.shape).astype(np.int16)
    pixels = np.clip(pixels.astype(np.int16) + noise_mask, 0, 255).astype(np.uint8)
    img = Image.fromarray(pixels)

    # Adiciona "montanhas" simples se keyword bate
    if any(k in prompt_l for k in ["mountain", "alpine", "snow"]):
        for _ in range(8):
            cx = rng.randint(0, width)
            base_y = rng.randint(horizon_y - 50, horizon_y + 100)
            height_m = rng.randint(80, 200)
            points = [(cx - height_m, height), (cx, base_y), (cx + height_m, height)]
            color = (
                rng.randint(180, 230),
                rng.randint(180, 220),
                rng.randint(190, 240),
            )
            draw.polygon(points, fill=color, outline=color)

    out_path = "/tmp/worldgen_fallback_pano.jpg"
    img.save(out_path, quality=85)
    return out_path


def generate_panorama_with_flux(
    prompt: str,
    output_path: str,
    hf_token: str,
    resolution: int = 1024,
) -> str:
    """
    Tenta gerar panorama usando FLUX.1-dev (gated, requer licença aceita).

    Args:
        prompt: text prompt
        output_path: onde salvar panorama gerada
        hf_token: HF token
        resolution: largura (altura = resolution/2)
    """
    try:
        import torch
        from huggingface_hub import login
        from diffusers import FluxPipeline

        login(token=hf_token)

        pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-dev",
            torch_dtype=torch.bfloat16,
        )
        # Se houver GPU, usa
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
        else:
            # CPU é MUITO lento pra FLUX. Avisa e tenta mesmo assim.
            pipe = pipe.to("cpu")
            print("[t2mesh] WARN: FLUX em CPU vai ser EXTREMAMENTE lento (~30+ min)")

        img = pipe(
            prompt=f"360 degree equirectangular panorama, {prompt}, high quality, photorealistic",
            width=resolution,
            height=resolution // 2,
            num_inference_steps=20,
            guidance_scale=3.5,
        ).images[0]

        img.save(output_path, quality=90)
        return output_path
    except Exception as e:
        raise RuntimeError(f"FLUX falhou: {e}")


def main():
    p = argparse.ArgumentParser(
        description="Text → 3D mesh (CPU-compatible). Adapta WorldGen sem FLUX.",
    )
    p.add_argument("--prompt", required=True, help="Text prompt")
    p.add_argument("--output", required=True, help="Output .ply")
    p.add_argument("--obj", help="Também exportar .obj")
    p.add_argument("--method", default="poisson")
    p.add_argument("--downscale", type=int, default=8)
    p.add_argument("--resolution", type=int, default=1024)
    p.add_argument("--hf-token", help="HF token (opcional, pra usar FLUX real)")
    p.add_argument("--fallback-procedural", action="store_true",
                   help="se FLUX falhar, gera panorama procedural")
    p.add_argument("--save-panorama", help="Salvar panorama usada")
    args = p.parse_args()

    out_ply = Path(args.output)
    out_ply.parent.mkdir(parents=True, exist_ok=True)
    save_pano = args.save_panorama or "/tmp/worldgen_pano.jpg"

    # 1. Gera panorama
    hf_token = args.hf_token
    if not hf_token:
        import os
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

    panorama_path = None
    if hf_token:
        try:
            print(f"[t2mesh] tentando FLUX.1-dev com HF token...")
            panorama_path = generate_panorama_with_flux(
                args.prompt, save_pano, hf_token, args.resolution,
            )
        except Exception as e:
            print(f"[t2mesh] FLUX falhou: {e}")
            if not args.fallback_procedural:
                print("[t2mesh] use --fallback-procedural pra gerar panorama sem FLUX")
                return 1

    if panorama_path is None:
        print(f"[t2mesh] usando fallback procedural: '{args.prompt}'")
        panorama_path = generate_panorama_procedural(args.prompt, args.resolution)
        # salva cópia se pedido
        if args.save_panorama:
            import shutil
            shutil.copy(panorama_path, args.save_panorama)
            panorama_path = args.save_panorama

    # 2. i2mesh pipeline
    print(f"[t2mesh] panorama: {panorama_path}")
    print(f"[t2mesh] gerando mesh...")

    # chama i2mesh programaticamente
    from .i2mesh import main as i2mesh_main
    sys.argv = [
        "i2mesh",
        "--input", panorama_path,
        "--output", str(out_ply),
        "--method", args.method,
        "--downscale", str(args.downscale),
    ]
    if args.obj:
        sys.argv.extend(["--obj", args.obj])
    return i2mesh_main()


if __name__ == "__main__":
    sys.exit(main())