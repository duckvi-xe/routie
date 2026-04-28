#!/usr/bin/env bash
# ==============================================================================
#  download-osm.sh — Download OSM extracts for GraphHopper
#
#  Downloads a regional OSM PBF file for GraphHopper routing.
#  By default downloads the Lombardy region (~50MB).
#  For all of Italy, use:  ./scripts/download-osm.sh italy
#  For custom regions, set: OSM_URL=<url> ./scripts/download-osm.sh
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OSM_DIR="${PROJECT_DIR}/data/osm"
OSM_FILE="${OSM_DIR}/italy-latest.osm.pbf"

# Region presets
LOMBARDY_URL="https://download.geofabrik.de/europe/italy/nord-est-latest.osm.pbf"
ITALY_URL="https://download.geofabrik.de/europe/italy-latest.osm.pbf"

# Use environment override or default to Lombardy
OSM_URL="${OSM_URL:-${LOMBARDY_URL}}"

# Allow named presets
case "${1:-lombardy}" in
  italy)
    OSM_URL="${ITALY_URL}"
    OSM_FILE="${OSM_DIR}/italy-latest.osm.pbf"
    ;;
  lombardy)
    # geofabrik doesn't have a standalone lombardy; use north-east italy
    OSM_URL="https://download.geofabrik.de/europe/italy/nord-est-latest.osm.pbf"
    OSM_FILE="${OSM_DIR}/nord-est-latest.osm.pbf"
    ;;
  milan)
    # Protomaps extracts — very small, great for dev
    OSM_URL="https://download.geofabrik.de/europe/italy-latest.osm.pbf"
    # For truly minimal: use bbox extract tool
    echo "No standalone Milan extract. Downloading Italy and importing all."
    ;;
  *)
    if [[ -n "${OSM_URL:-}" ]]; then
      OSM_FILE="${OSM_DIR}/custom.osm.pbf"
    fi
    ;;
esac

# Create directory
mkdir -p "${OSM_DIR}"

# Check if already downloaded
if [[ -f "${OSM_FILE}" ]]; then
  echo "✓ OSM data already exists: ${OSM_FILE}"
  echo "  Size: $(du -h "${OSM_FILE}" | cut -f1)"
  echo "  To re-download, delete the file first: rm ${OSM_FILE}"
  exit 0
fi

echo "⟳ Downloading OSM data from:"
echo "   ${OSM_URL}"
echo "   → ${OSM_FILE}"
echo ""
echo "   This may take a few minutes depending on file size..."
echo ""

# Download with curl (resume support)
curl -fL --retry 3 --retry-delay 5 -C - -o "${OSM_FILE}" "${OSM_URL}"

echo ""
echo "✓ Downloaded: ${OSM_FILE}"
echo "  Size: $(du -h "${OSM_FILE}" | cut -f1)"
echo ""
echo "  Next step: start GraphHopper with:"
echo "    docker compose --profile graphhopper up -d"
echo ""
echo "  Note: First import will take 2-10 minutes depending on file size."
