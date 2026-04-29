#!/usr/bin/env bash
# =============================================================================
#  download_osm.sh — Download OSM extracts for Valhalla routing
# =============================================================================
#  Downloads OSM PBF files and places them in data/osm/, which is mounted
#  into the Valhalla container at /custom_files/.
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
#  Requirements: curl, python3
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

# ---------------------------------------------------------------------------
#  verify_pbf <file> — validates an OSM PBF file header using Python
# ---------------------------------------------------------------------------
verify_pbf() {
    local file="$1"
    if [ ! -f "$file" ]; then
        err "File not found: ${file}"
        return 1
    fi
    python3 -c "
import struct, sys
try:
    with open('${file}', 'rb') as f:
        data = f.read(4)
        if len(data) < 4:
            sys.exit(1)  # too small
        blob_len = struct.unpack('>I', data)[0]
        if blob_len <= 0 or blob_len > 100 * 1024 * 1024:
            sys.exit(2)  # improbable blob length
        header = f.read(min(blob_len, 200))
        if b'OSMHeader' not in header and b'OSMData' not in header:
            sys.exit(3)  # not a valid OSM PBF
        sys.exit(0)  # valid
except Exception:
    sys.exit(4)
" && return 0
    local rc=$?
    case $rc in
        1) err "File truncated (too small to be a valid PBF)";;
        2) err "Invalid blob length (corrupted or truncated PBF)";;
        3) err "Not a valid OSM PBF file (missing OSMHeader/OSMData marker)";;
        4) err "Python error while validating PBF";;
        *) err "Unknown validation error (exit code ${rc})";;
    esac
    return 1
}

# ---------------------------------------------------------------------------

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
        if verify_pbf "$OUT"; then
            ok "Integrity check passed: ${OUT}"
        else
            err "Existing PBF is corrupted — deleting and re-downloading."
            rm -f "$OUT"
        fi
    fi

    if [ ! -f "$OUT" ]; then
        info "Downloading ${URL}"
        curl -fSL -o "$OUT" "$URL" || { err "Download failed"; exit 1; }
        ok "Downloaded: ${OUT} ($(du -h "$OUT" | cut -f1))"
        if verify_pbf "$OUT"; then
            ok "Integrity check passed: ${OUT}"
        else
            err "Downloaded PBF is corrupted — the file may be incomplete."
            err "Try again: the Geofabrik mirror may have been flaky."
            err "If the error persists, check your internet connection."
            exit 1
        fi
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
