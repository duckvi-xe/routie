#!/usr/bin/env bash
# =============================================================================
#  setup_valhalla.sh — Download OSM data and start Valhalla routing engine
# =============================================================================
#  This script helps you set up Valhalla for the first time. It:
#    1. Downloads an OSM extract (PBF) for your region of choice
#    2. Starts the Valhalla Docker container, which builds the routing tiles
#    3. Restarts Routie with ROUTE_PROVIDER=valhalla
#
#  Usage:
#    ./scripts/setup_valhalla.sh [region]
#
#  Examples:
#    ./scripts/setup_valhalla.sh italy
#    ./scripts/setup_valhalla.sh andorra          # quick test — very small!
#    ./scripts/setup_valhalla.sh "italy,switzerland"  # multiple regions
#
#  Regions: any area from https://download.geofabrik.de
#  Default: andorra (small, fast for testing)
#
#  Requirements:
#    - Docker & docker compose
#    - curl, xz (for download)
#    - ~2-8 GB free disk per region
# =============================================================================

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

# ── Config ──────────────────────────────────────────────────────────────────
REGION="${1:-andorra}"
OSM_DIR="./data/osm"
VALHALLA_PROFILE="valhalla"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Pre-flight checks ───────────────────────────────────────────────────────
command -v docker &>/dev/null || { err "Docker is not installed."; exit 1; }
docker compose version &>/dev/null || { err "docker compose plugin is required."; exit 1; }

# ── Step 1: Download OSM extract ────────────────────────────────────────────
info "Step 1/3: Downloading OSM data for region(s): ${REGION}"

mkdir -p "$OSM_DIR"

# Parse comma-separated regions
IFS=',' read -ra REGIONS <<< "$REGION"
PBF_FILES=()

for region in "${REGIONS[@]}"; do
    region="$(echo "$region" | xargs)"  # trim whitespace
    region_lower="$(echo "$region" | tr '[:upper:]' '[:lower:]')"

    # Build download URL (Geofabrik)
    # Special cases for well-known regions
    case "$region_lower" in
        italy|switzerland|austria|france|germany|spain|uk|great-britain|netherlands|belgium)
            URL="https://download.geofabrik.de/europe/${region_lower}-latest.osm.pbf"
            ;;
        andorra|liechtenstein|monaco|luxembourg|san-marino|vatican)
            URL="https://download.geofabrik.de/europe/${region_lower}-latest.osm.pbf"
            ;;
        north-america|south-america|asia|africa|australia-oceania)
            URL="https://download.geofabrik.de/${region_lower}-latest.osm.pbf"
            ;;
        *)
            # Try directly — user may know the exact path
            URL="https://download.geofabrik.de/${region_lower}-latest.osm.pbf"
            ;;
    esac

    PBF_FILE="${OSM_DIR}/${region_lower}-latest.osm.pbf"

    if [ -f "$PBF_FILE" ]; then
        ok "OSM data already exists: ${PBF_FILE}"
    else
        echo -e "  ${CYAN}Downloading${NC} ${URL}"
        curl -fSL -o "$PBF_FILE" "$URL" || {
            err "Failed to download ${URL}"
            err "Check available regions at https://download.geofabrik.de"
            exit 1
        }
        ok "Downloaded: ${PBF_FILE} ($(du -h "$PBF_FILE" | cut -f1))"
    fi
    PBF_FILES+=("$PBF_FILE")
done

# ── Step 2: Start Valhalla container ────────────────────────────────────────
info "Step 2/3: Starting Valhalla with profile '${VALHALLA_PROFILE}'"

# Export variables for docker-compose
export VALHALLA_REBUILD=true
export VALHALLA_THREADS="${VALHALLA_THREADS:-$(nproc)}"
export ROUTE_PROVIDER="${ROUTE_PROVIDER:-valhalla}"

# Copy the PBF files into the Valhalla custom_files volume
# We rely on the docker-compose volume mount: valhalla-custom -> /custom_files
# The gis-ops image detects .pbf files in /custom_files and imports them.
# We place them where the docker-compose volume binding can pick them up.
echo "  Placing OSM data for Valhalla import..."

# Create a custom_files directory that gets mounted into the container
mkdir -p custom_files
for pbf in "${PBF_FILES[@]}"; do
    cp "$pbf" custom_files/
    ok "  Staged: $(basename "$pbf")"
done

# Also copy the valhalla.json config
cp config/valhalla.json custom_files/

info "Starting Valhalla container (first import may take 5-30 min)..."
docker compose --profile "$VALHALLA_PROFILE" up -d valhalla

# ── Step 3: Wait for Valhalla to be ready ───────────────────────────────────
info "Step 3/3: Waiting for Valhalla to be ready (polling /status)..."
ATTEMPTS=0
MAX_ATTEMPTS=120  # 10 minutes max

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if docker compose exec -T valhalla curl -sf http://localhost:8002/status &>/dev/null 2>&1; then
        ok "Valhalla is ready at http://localhost:8002"
        break
    fi
    # Alternative check via host port
    if curl -sf http://localhost:8002/status &>/dev/null 2>&1; then
        ok "Valhalla is ready at http://localhost:8002"
        break
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ $((ATTEMPTS % 6)) -eq 0 ]; then
        echo "  Still waiting... ($((ATTEMPTS * 5)) seconds elapsed)"
    fi
    sleep 5
done

if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
    warn "Timed out waiting for Valhalla. Check logs: docker compose logs valhalla"
    warn "Valhalla may still be building tiles in the background."
    warn "You can monitor it with: docker compose logs --tail=50 -f valhalla"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Valhalla setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Valhalla URL:  http://localhost:8002"
echo "  OSM data:      ${OSM_DIR}/"
echo ""
echo "  To test routing via Valhalla directly:"
echo "    curl -X POST http://localhost:8002/route \\"
echo '      -H "Content-Type: application/json" \'
echo '      -d '"'"'{"costing":"pedestrian","locations":[{"lat":41.89,"lon":12.49},{"lat":41.90,"lon":12.50}]}'"'"''
echo ""
echo "  To start Routie with Valhalla:"
echo "    ROUTE_PROVIDER=valhalla docker compose up -d backend"
echo ""
echo "  Or set ROUTE_PROVIDER=valhalla in your .env file."
echo ""
echo "  To check Valhalla logs:"
echo "    docker compose logs --tail=50 valhalla"
echo ""

# ── Cleanup: remove staged PBFs (they're also in data/osm/) ─────────────────
rm -f custom_files/*.osm.pbf
