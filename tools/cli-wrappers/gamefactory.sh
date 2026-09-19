#!/usr/bin/env bash
# =============================================================================
# gamefactory.sh — STUB: GameFactory-3A gen_3d_scene / gen_3d_object
# =============================================================================
# Status: AGUARDANDO LINK DO FRAMEWORK
# =============================================================================
set -euo pipefail

cat <<EOF
[gamefactory.sh] ============================================
                  STUB — aguardando framework
============================================

GameFactory-3A — operadores tipados para geração de objetos e cenas.

Quando o link for fornecido:

  gamefactory gen_3d_object \\
      --type <tree|rock|building|...> \\
      --style <...> \\
      --seed <int> \\
      --output <path/to/object.glb>

  gamefactory gen_3d_scene \\
      --prompt "..." \\
      --density <low|medium|high> \\
      --biome <mediterranean|temperate|...> \\
      --bounds <min_x,min_y,max_x,max_y> \\
      --output <path/to/scene/>

Por enquanto, sem geração real.
EOF
