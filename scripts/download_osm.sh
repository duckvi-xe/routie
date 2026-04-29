#!/usr/bin/env bash
# =============================================================================
#  download_osm.sh — Download OSM extracts for Valhalla routing
# =============================================================================
#  Downloads OSM PBF files and places them in data/osm/, which is mounted
#  into the Valhalla container at /custom_files/osm/.
#
#  Usage:
#    ./scripts/download_osm.sh [region]
#
#  Examples:
#    ./scripts/download_osm.sh andorra            # quick test (~5 MB)
#    ./scripts/download_osm.sh italy              # production (~1.5 GB)
#    ./scripts/download_osm.sh "italy,switzerland"  # multiple regions
#
#  Regions: any area from https://download.geofabrik.de
#  Default: andorra (small, fast for testing)
#
#  Requirements: curl
# =============================================================================

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

REGION="${1:-andorra}"
OSM_DIR="./data/osm"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

mkdir -p "$OSM_DIR"

IFS=',' read -ra REGIONS <<< "$REGION"

for region in "${REGIONS[@]}"; do
    region="$(echo "$region" | xargs)"
    rl="$(echo "$region" | tr '[:upper:]' '[:lower:]')"

    case "$rl" in
        italy|switzerland|austria|france|germany|spain|uk|great-britain|netherlands|belgium)
            URL="https://download.geofabrik.de/europe/${rl}-latest.osm.pbf"
            ;;
        andorra|liechtenstein|monaco|luxembourg|san-marino|vatican)
            URL="https://download.geofabrik.de/europe/${rl}-latest.osm.pbf"
            ;;
        north-america|south-america|asia|africa|australia-oceania)
            URL="https://download.geofabrik.de/${rl}-latest.osm.pbf"
            ;;
        *)
            URL="https://download.geofabrik.de/${rl}-latest.osm.pbf"
            ;;
    esac

    OUT="${OSM_DIR}/${rl}-latest.osm.pbf"

    if [ -f "$OUT" ]; then
        ok "Already exists: ${OUT}"
    else
        info "Downloading ${URL}"
        curl -fSL -o "$OUT" "$URL" || { err "Download failed"; exit 1; }
        ok "Downloaded: ${OUT} ($(du -h "$OUT" | cut -f1))"
    fi
done

echo ""
echo "OSM data ready in ${OSM_DIR}/"
echo ""
echo "To start Valhalla + Routie:"
echo "  docker compose --profile valhalla up -d"
echo ""
echo "OSM files in data/osm/ are auto-mounted at /custom_files/"
echo "in the Valhalla container. Set VALHALLA_REBUILD=true for first import."
