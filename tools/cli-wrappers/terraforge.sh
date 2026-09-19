#!/usr/bin/env bash
# =============================================================================
# terraforge.sh — STUB: Terreno procedural (TerraForge3D)
# =============================================================================
# Status: AGUARDANDO LINK DO FRAMEWORK
# Quando você fornecer o repo/binário, este wrapper será preenchido.
# =============================================================================
set -euo pipefail

cat <<EOF
[terraforge.sh] ============================================
                  STUB — aguardando framework
============================================

Esta é uma implementação placeholder. Quando você passar o
link do TerraForge3D (ou framework equivalente), este wrapper
será preenchido com a CLI real.

Esqueleto previsto:

  terraforge generate \\
      --biome <coastal|mountain|desert|forest|tundra|volcanic|grassland> \\
      --size-km <float> \\
      --resolution <int> \\
      --seed <int> \\
      --features <erosion,rivers,caves> \\
      --output <path/to/terrain.glb>

Saída esperada:
  - heightmap.png (16-bit)
  - splat_map.png (camadas PBR)
  - terrain.glb (mesh pronta para engine)

Por enquanto, fallback para Python puro:
EOF

# Fallback: gerar heightmap sintético via opensimplex
if command -v python3 >/dev/null 2>&1 && python3 -c "import opensimplex" 2>/dev/null; then
  SIZE="\${1:-2048}"
  python3 - <<'PY'
from opensimplex import OpenSimplex
from PIL import Image
import numpy as np
import sys

size = int(sys.argv[1]) if len(sys.argv) > 1 else 2048
gen = OpenSimplex(seed=42)
heightmap = np.zeros((size, size), dtype=np.float32)
for y in range(size):
    for x in range(size):
        nx, ny = x/size - 0.5, y/size - 0.5
        amp, freq, total = 1.0, 1.0, 0.0
        for o in range(6):
            total += gen.noise2(nx*freq*8, ny*freq*8) * amp
            amp *= 0.5; freq *= 2.0
        heightmap[y, x] = (total + 1) / 2

img = Image.fromarray((heightmap * 65535).astype(np.uint16), mode="I;16")
img.save("./heightmap.png")
print("[fallback] heightmap.png gerado (substitua quando TerraForge3D chegar)")
PY
else
  echo "[terraforge.sh] Python opensimplex não disponível; instale com: pip install opensimplex pillow numpy"
  exit 1
fi
