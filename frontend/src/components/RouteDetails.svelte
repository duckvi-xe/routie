<script>
  let { route, onReset } = $props();

  const DIFFICULTY_COLORS = {
    easy: "#22c55e",
    moderate: "#eab308",
    hard: "#ef4444",
  };

  const DIFFICULTY_LABELS = {
    easy: "Facile",
    moderate: "Moderato",
    hard: "Difficile",
  };

  const ACTIVITY_LABELS = {
    running: "Corsa",
    cycling: "Ciclismo",
  };

  // Format duration
  function formatDuration(min) {
    if (min >= 60) {
      const h = Math.floor(min / 60);
      const m = min % 60;
      return m > 0 ? `${h}h ${m}m` : `${h}h`;
    }
    return `${min} min`;
  }

  // Estimated pace (min per km)
  function formatPace(distanceKm, durationMin) {
    if (!distanceKm || distanceKm <= 0) return "-";
    const pace = durationMin / distanceKm;
    const min = Math.floor(pace);
    const sec = Math.round((pace - min) * 60);
    return `${min}:${sec.toString().padStart(2, "0")} /km`;
  }
</script>

<div class="route-result">
  <div class="result-header">
    <h3 class="result-title">{route.name}</h3>
    <span
      class="difficulty-badge"
      style="background: {DIFFICULTY_COLORS[route.difficulty]}20;
             color: {DIFFICULTY_COLORS[route.difficulty]};
             border: 1px solid {DIFFICULTY_COLORS[route.difficulty]}40;"
    >
      {DIFFICULTY_LABELS[route.difficulty] || route.difficulty}
    </span>
  </div>

  <div class="metrics-grid">
    <div class="metric">
      <span class="metric-value">{route.distance_km.toFixed(1)}</span>
      <span class="metric-unit">km</span>
      <span class="metric-label">Distanza</span>
    </div>

    <div class="metric">
      <span class="metric-value">{route.elevation_gain_m.toFixed(0)}</span>
      <span class="metric-unit">m</span>
      <span class="metric-label">Dislivello</span>
    </div>

    <div class="metric">
      <span class="metric-value">{formatDuration(route.estimated_duration_min)}</span>
      <span class="metric-label">Durata stimata</span>
    </div>

    <div class="metric">
      <span class="metric-value">{formatPace(route.distance_km, route.estimated_duration_min)}</span>
      <span class="metric-label">Ritmo medio</span>
    </div>
  </div>

  <div class="result-meta">
    <span class="meta-chip">{ACTIVITY_LABELS[route.activity_type] || route.activity_type}</span>
    <span class="meta-chip">{route.waypoints.length} waypoints</span>
  </div>

  <button class="btn-secondary" onclick={onReset}>
    Nuovo Percorso
  </button>
</div>

<style>
  .route-result {
    margin-top: 1rem;
    padding: 1rem;
    background: linear-gradient(135deg, #0f172a 0%, #1a2332 100%);
    border: 1px solid #334155;
    border-radius: 12px;
  }

  .result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
  }

  .result-title {
    font-size: 1rem;
    font-weight: 600;
    color: #e2e8f0;
  }

  .difficulty-badge {
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .metric {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.6rem;
    background: #1e293b;
    border-radius: 8px;
  }

  .metric-value {
    font-size: 1.1rem;
    font-weight: 700;
    color: #60a5fa;
  }

  .metric-unit {
    font-size: 0.7rem;
    color: #64748b;
    margin-left: 0.1rem;
  }

  .metric-label {
    font-size: 0.65rem;
    color: #64748b;
    text-transform: uppercase;
    margin-top: 0.15rem;
  }

  .result-meta {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .meta-chip {
    padding: 0.2rem 0.6rem;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 0.75rem;
    color: #94a3b8;
  }

  .btn-secondary {
    width: 100%;
    padding: 0.6rem;
    background: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-secondary:hover {
    background: #334155;
    color: #e2e8f0;
  }
</style>
