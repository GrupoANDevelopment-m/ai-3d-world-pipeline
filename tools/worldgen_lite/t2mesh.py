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
    Fallback procedural sem FLUX. Usa procedural_pano.py que detecta biomas
    (snow, mountain, forest, city, desert, ocean, beach, sunset, etc.)
    e gera panoramas ricas com:
      - Sky gradient + sol/lua/estrelas
      - Terrain com features específicas do bioma
      - Noise variation pra depth estimator

    Mesmo prompt = mesmo output (seed via md5).
    """
    from .procedural_pano import save
    out_path = "/tmp/worldgen_fallback_pano.jpg"
    save(prompt, out_path, width, height)
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