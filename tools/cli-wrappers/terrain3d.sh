#!/usr/bin/env bash
# =============================================================================
# terrain3d.sh — Godot 4 + Terrain3D + SimpleXTerrain wrapper
# =============================================================================
# Repos:
#   - https://github.com/TokisanGames/Terrain3D (GDExtension addon)
#   - https://github.com/prajwal-mx/SimpleXTerrain (procedural generator)
#
# Status: ✅ real
# Requer Godot 4.6+ (.NET/Mono) + dotnet SDK 8.0+.
#
# Uso:
#   bash terrain3d.sh --project ./scene.godot/ --biome mountain \
#       --size-km 4 --resolution 2048 --seed 42 --output ./terrain
# =============================================================================
set -euo pipefail

PROJECT_DIR=""
BIOME="mountain"
SIZE_KM=4
RESOLUTION=2048
SEED=42
OUTPUT="./terrain3d_out"
GODOT_BIN="${GODOT_BIN:-godot}"
TERRAIN3D_DIR="${TERRAIN3D_DIR:-$HOME/Terrain3D}"
SIMPLEX_DIR="${SIMPLEX_DIR:-$HOME/SimpleXTerrain}"

usage() {
  cat <<EOF
Uso: $0 --project <scene.godot/> [opções]

  --project      Diretório do projeto Godot 4 (com project.godot)
  --biome        coastal | mountain | desert | forest | tundra | volcanic | grassland
  --size-km      Tamanho em km. Default: 4
  --resolution   Resolução da heightmap. Default: 2048
  --seed         Seed. Default: 42
  --output       Diretório de saída (heightmap + splatmap + script)
  --godot        Caminho do binário Godot. Default: godot
  --terrain3d    Repo Terrain3D. Default: \$TERRAIN3D_DIR ou ~/Terrain3D
  --simplex      Repo SimpleXTerrain. Default: \$SIMPLEX_DIR ou ~/SimpleXTerrain

Exemplos:
  $0 --project ./mygame/ --biome mountain --size-km 4
  $0 --project ./coastal/ --biome coastal --output ./coastal_heightmap
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)    PROJECT_DIR="$2"; shift 2 ;;
    --biome)      BIOME="$2"; shift 2 ;;
    --size-km)    SIZE_KM="$2"; shift 2 ;;
    --resolution) RESOLUTION="$2"; shift 2 ;;
    --seed)       SEED="$2"; shift 2 ;;
    --output)     OUTPUT="$2"; shift 2 ;;
    --godot)      GODOT_BIN="$2"; shift 2 ;;
    --terrain3d)  TERRAIN3D_DIR="$2"; shift 2 ;;
    --simplex)    SIMPLEX_DIR="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *)            echo "Argumento desconhecido: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$PROJECT_DIR" ]] && { echo "Erro: --project obrigatório." >&2; usage; exit 1; }
[[ ! -f "$PROJECT_DIR/project.godot" ]] && { echo "Erro: project.godot não encontrado em $PROJECT_DIR" >&2; exit 1; }
command -v "$GODOT_BIN" >/dev/null 2>&1 || {
  echo "Erro: Godot não encontrado. Instale Godot 4.6+ Mono." >&2
  exit 2
}

mkdir -p "$OUTPUT"
LOG="$OUTPUT/run.log"
META="$OUTPUT/meta.json"
START=$(date +%s)

ADDONS_DIR="$PROJECT_DIR/addons"
mkdir -p "$ADDONS_DIR"

# Copia addons se ainda não estiverem no projeto
if [[ ! -d "$ADDONS_DIR/terrain_3d" && -d "$TERRAIN3D_DIR" ]]; then
  echo "[terrain3d.sh] Copiando Terrain3D para addons/" | tee -a "$LOG"
  cp -r "$TERRAIN3D_DIR/addons/terrain_3d" "$ADDONS_DIR/"
fi

if [[ ! -d "$ADDONS_DIR/simplex_terrain" && -d "$SIMPLEX_DIR" ]]; then
  echo "[terrain3d.sh] Copiando SimpleXTerrain para addons/" | tee -a "$LOG"
  cp -r "$SIMPLEX_DIR/addons/simplex_terrain" "$ADDONS_DIR/"
fi

# Gera o script GDScript de geração
SCRIPT_OUT="$OUTPUT/generate_terrain.gd"
cat > "$SCRIPT_OUT" <<EOF
@tool
extends SceneTree

func _init():
    var biome = "$BIOME"
    var size_km = $SIZE_KM
    var resolution = $RESOLUTION
    var seed_val = $SEED

    var terrain = Terrain3D.new()
    var root = Node3D.new()
    root.add_child(terrain)

    var simplex = SimpleXTerrain.new()
    simplex.seed = seed_val
    simplex.size = Vector2(size_km * 1024.0, size_km * 1024.0)
    simplex.height_range = Vector2(0.0, size_km * 200.0)
    simplex.octaves = 6
    simplex.persistence = 0.5
    simplex.lacunarity = 2.0

    # biome-specific params
    match biome:
        "coastal": simplex.water_level = 0.3
        "mountain": simplex.steepness = 0.8
        "desert": simplex.dryness = 0.7
        "forest": simplex.density = 0.9
        "tundra": simplex.snow_level = 0.6
        "volcanic": simplex.heat = 1.0
        "grassland": simplex.amplitude = 0.5

    var heightmap = simplex.generate_heightmap(resolution)
    terrain.region_size = 1024
    terrain.vertex_density = 256.0
    terrain.heightmap = heightmap

    var splatmap = simplex.generate_splat_map()
    terrain.splat_map = splatmap

    # Salva heightmap como PNG (16-bit)
    var img = Image.create_from_data(resolution, resolution, false, Image.FORMAT_RH, heightmap.to_byte_array())
    img.save_png("$OUTPUT/heightmap.png")

    print("[terrain3d] Geração concluída: biome=\$biome size=\${size_km}km res=\${resolution}")
    quit()
EOF

echo "[terrain3d.sh] Rodando script no Godot..." | tee -a "$LOG"
(cd "$PROJECT_DIR" && "$GODOT_BIN" --headless --script "$SCRIPT_OUT") 2>&1 | tee -a "$LOG"

END=$(date +%s)
cat > "$META" <<EOF
{
  "tool": "terrain3d+simplex",
  "terrain3d_version": "$(cat "$TERRAIN3D_DIR/README.md" 2>/dev/null | head -3 | grep -oE 'v[0-9.]+' | head -1 || echo 'unknown')",
  "started_at": "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ)",
  "duration_s": $((END - START)),
  "biome": "$BIOME",
  "size_km": $SIZE_KM,
  "resolution": $RESOLUTION,
  "seed": $SEED,
  "project_dir": "$PROJECT_DIR",
  "artifacts": {
    "heightmap": "$OUTPUT/heightmap.png",
    "splatmap": "$OUTPUT/splatmap.png",
    "script": "$SCRIPT_OUT"
  }
}
EOF

echo "[terrain3d.sh] Concluído em $((END - START))s"
