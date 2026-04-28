<script>
  import { onMount, onDestroy, tick } from "svelte";
  import L from "leaflet";

  let { waypoints = [] } = $props();

  let mapContainer;
  let map;
  let polylineLayer;
  let markerLayer = [];
  let userMarker;
  let initialized = false;

  // Default: Milan city center
  const DEFAULT_CENTER = [45.4642, 9.19];
  const DEFAULT_ZOOM = 13;

  onMount(() => {
    map = L.map(mapContainer, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      zoomControl: true,
      scrollWheelZoom: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    // Try geolocation
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords;
          map.setView([latitude, longitude], DEFAULT_ZOOM);
          userMarker = L.circleMarker([latitude, longitude], {
            radius: 8,
            fillColor: "#3b82f6",
            color: "#60a5fa",
            weight: 2,
            opacity: 1,
            fillOpacity: 0.6,
          })
            .addTo(map)
            .bindPopup("La tua posizione");
        },
        () => {
          // Geolocation failed, keep default center
        },
        { enableHighAccuracy: true, timeout: 5000 },
      );
    }

    initialized = true;
  });

  onDestroy(() => {
    if (map) {
      map.remove();
      map = null;
    }
  });

  // Watch waypoints changes to update the route on the map
  $effect(() => {
    const wps = waypoints;
    if (!initialized || !map || !wps || wps.length === 0) {
      return;
    }

    // Remove previous route
    if (polylineLayer) {
      map.removeLayer(polylineLayer);
    }
    markerLayer.forEach((m) => map.removeLayer(m));
    markerLayer = [];

    // Convert waypoints to leaflet latlngs
    const latlngs = wps.map(
      (wp) => [wp.latitude, wp.longitude],
    );

    // Draw the polyline
    polylineLayer = L.polyline(latlngs, {
      color: "#60a5fa",
      weight: 4,
      opacity: 0.8,
      lineJoin: "round",
    }).addTo(map);

    // Start marker (green)
    const startIcon = L.divIcon({
      html: `<div style="width:12px;height:12px;background:#22c55e;border:2px solid #fff;border-radius:50%;"></div>`,
      className: "",
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });
    const startMarker = L.marker(latlngs[0], { icon: startIcon })
      .addTo(map)
      .bindTooltip("Partenza", { permanent: false, direction: "top" });
    markerLayer.push(startMarker);

    // End marker (red)
    const endIcon = L.divIcon({
      html: `<div style="width:12px;height:12px;background:#ef4444;border:2px solid #fff;border-radius:50%;"></div>`,
      className: "",
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });
    const endMarker = L.marker(latlngs[latlngs.length - 1], { icon: endIcon })
      .addTo(map)
      .bindTooltip("Arrivo", { permanent: false, direction: "top" });
    markerLayer.push(endMarker);

    // Fit map to route bounds
    const bounds = L.latLngBounds(latlngs);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
  });
</script>

<div class="map-wrapper" bind:this={mapContainer}></div>

<style>
  .map-wrapper {
    width: 100%;
    height: 100%;
    min-height: 100vh;
  }

  .map-wrapper :global(.leaflet-container) {
    background: #1e293b;
  }

  .map-wrapper :global(.leaflet-control-zoom a) {
    background: #1e293b;
    color: #e2e8f0;
    border-color: #334155;
  }

  .map-wrapper :global(.leaflet-control-zoom a:hover) {
    background: #334155;
  }

  .map-wrapper :global(.leaflet-control-attribution) {
    background: rgba(15, 23, 42, 0.8) !important;
    color: #64748b;
    font-size: 0.7rem;
  }

  .map-wrapper :global(.leaflet-control-attribution a) {
    color: #60a5fa;
  }
</style>
