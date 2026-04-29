#!/bin/sh
# =============================================================================
#  docker-entrypoint.sh — Routie Docker entrypoint
# =============================================================================
#  When ROUTE_PROVIDER=valhalla, waits for Valhalla's health endpoint before
#  starting the backend. Otherwise starts immediately.
# =============================================================================

set -eu

if [ "${ROUTE_PROVIDER:-}" = "valhalla" ]; then
    url="${VALHALLA_URL:-http://valhalla:8002}/status"
    echo "Waiting for Valhalla at ${url} ..."
    i=0
    until curl -sf "$url" > /dev/null 2>&1; do
        i=$((i + 1))
        if [ $i -gt 60 ]; then
            echo "ERROR: Valhalla not ready after 60 attempts. Check valhalla logs."
            echo "Falling back to mock provider..."
            export ROUTE_PROVIDER=mock
            break
        fi
        sleep 2
    done
    if [ "${ROUTE_PROVIDER:-}" = "valhalla" ]; then
        echo "Valhalla is ready!"
    fi
else
    echo "ROUTE_PROVIDER=${ROUTE_PROVIDER:-mock} — skipping Valhalla wait."
fi

exec "$@"
