#!/usr/bin/env bash
# =============================================================================
# worldgen.sh — STUB: Text-to-3D scene (WorldGen / GameFactory-3A)
# =============================================================================
# Status: AGUARDANDO LINK DO FRAMEWORK
# =============================================================================
set -euo pipefail

cat <<EOF
[worldgen.sh] ============================================
                  STUB — aguardando framework
============================================

Esta é uma implementação placeholder. Quando você passar o
link do WorldGen (Microsoft) ou do GameFactory-3A, este wrapper
será preenchido com a CLI real.

Esqueleto previsto:

  worldgen generate \\
      --prompt "<texto em linguagem natural>" \\
      --style <realistic|stylized|anime|lowpoly> \\
      --reference-image <path> \\
      --seed <int> \\
      --output <path/to/scene.glb>

  gamefactory gen_3d_scene \\
      --prompt "..." \\
      --density <low|medium|high> \\
      --biome <...> \\
      --output <path>

Por enquanto, sem geração real.
EOF

echo "Para usar fallback procedural, veja tools/cli-wrappers/terraforge.sh"
