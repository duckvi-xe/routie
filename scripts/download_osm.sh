#!/usr/bin/env bash
# =============================================================================
#  download_osm.sh — Download OSM extracts for Valhalla routing
# =============================================================================
#  Downloads OSM PBF files (with MD5 integrity verification via Geofabrik's
#  checksum files) and places them in data/osm/, which is mounted into the
#  Valhalla container at /custom_files/.
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
#  Requirements: wget, md5sum
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
#  verify_md5 <pbf_path> <md5_url>
#    Downloads the .md5 checksum from Geofabrik, then verifies the PBF
#    file against it using md5sum.
# ---------------------------------------------------------------------------
verify_md5() {
    local pbf="$1"
    local md5_url="$2"
    local md5_file="${pbf}.md5"

    info "Downloading MD5 checksum from ${md5_url}"
    if ! wget -q -O "$md5_file" "$md5_url"; then
        err "Could not download MD5 checksum (${md5_url}) — skipping verification."
        rm -f "$md5_file"
        return 0
    fi

    local expected_hash
    expected_hash=$(awk '{print $1}' "$md5_file")

    if [ -z "$expected_hash" ]; then
        err "Empty MD5 checksum in ${md5_file} — skipping verification."
        rm -f "$md5_file"
        return 0
    fi

    local actual_hash
    actual_hash=$(md5sum "$pbf" | awk '{print $1}')

    rm -f "$md5_file"

    if [ "$expected_hash" = "$actual_hash" ]; then
        ok "MD5 checksum matches: ${expected_hash}"
        return 0
    else
        err "MD5 checksum MISMATCH"
        err "  Expected (Geofabrik): ${expected_hash}"
        err "  Actual   (local):     ${actual_hash}"
        return 1
    fi
}

# ---------------------------------------------------------------------------

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
        if verify_md5 "$OUT" "${URL}.md5"; then
            ok "Integrity check passed: ${OUT}"
        else
            err "Existing PBF has wrong checksum — deleting and re-downloading."
            rm -f "$OUT"
        fi
    fi

    if [ ! -f "$OUT" ]; then
        info "Downloading ${URL}"
        wget -O "$OUT" "$URL" || { err "Download failed"; exit 1; }
        ok "Downloaded: ${OUT} ($(du -h "$OUT" | cut -f1))"
        if verify_md5 "$OUT" "${URL}.md5"; then
            ok "Integrity check passed: ${OUT}"
        else
            err "Downloaded PBF failed MD5 verification — the file is corrupted."
            err "Try again: the Geofabrik mirror may have been flaky."
            err "If the error persists, check your internet connection."
            rm -f "$OUT"
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
