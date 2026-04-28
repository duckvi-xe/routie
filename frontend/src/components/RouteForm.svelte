<script>
  import { createEventDispatcher } from "svelte";

  let {
    profileId = null,
    loading = false,
  } = $props();

  const dispatch = createEventDispatcher();

  // Profile fields
  let name = $state("");
  let activityType = $state("running");
  let skillLevel = $state("intermediate");
  let customSpeed = $state("");

  // Route fields
  let maxDistance = $state("10");
  let maxDuration = $state("");
  let direction = $state("");
  let terrain = $state("");

  // State
  let isCreatingProfile = $state(false);
  let profileCreated = $state(false);
  let localLoading = $state(false);

  const isLoading = $derived(loading || localLoading);

  const API_BASE = "/api/v1";

  async function createProfile() {
    if (!name.trim()) {
      dispatch("error", "Inserisci un nome per il profilo");
      return null;
    }

    localLoading = true;
    try {
      const body = {
        name: name.trim(),
        activity_type: activityType,
        skill_level: skillLevel,
      };
      if (customSpeed) {
        body.avg_speed_kmh = parseFloat(customSpeed);
      }

      const resp = await fetch(`${API_BASE}/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail?.error?.message || err.detail || "Errore creazione profilo");
      }

      const profile = await resp.json();
      dispatch("profileCreated", { id: profile.id, name: profile.name });
      return profile.id;
    } catch (e) {
      dispatch("error", e.message);
      return null;
    } finally {
      localLoading = false;
    }
  }

  async function planRoute(pid) {
    localLoading = true;
    try {
      const body = {
        profile_id: pid,
        activity_type: activityType,
      };
      if (maxDistance) body.max_distance_km = parseFloat(maxDistance);
      if (maxDuration) body.max_duration_min = parseInt(maxDuration, 10);
      if (direction) body.preferred_direction = direction;
      if (terrain) body.terrain_type = terrain;

      const resp = await fetch(`${API_BASE}/routes/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail?.error?.message || err.detail || "Errore generazione percorso");
      }

      const route = await resp.json();
      dispatch("routeGenerated", route);
    } catch (e) {
      dispatch("error", e.message);
    } finally {
      localLoading = false;
    }
  }

  async function handleSubmit() {
    dispatch("error", ""); // clear errors

    let pid = profileId;
    if (!pid) {
      pid = await createProfile();
      if (!pid) return;
    }

    await planRoute(pid);
  }
</script>

<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="route-form">
  <!-- Profile Section -->
  <fieldset class="fieldset">
    <legend class="legend">
      <span class="legend-icon">1</span> Profilo
    </legend>

    <div class="form-group">
      <label for="name" class="label">Nome</label>
      <input
        id="name"
        type="text"
        bind:value={name}
        placeholder="es. Andrea"
        class="input"
        disabled={isLoading}
        required
      />
    </div>

    <div class="form-group">
      <label for="activity" class="label">Attivita</label>
      <select id="activity" bind:value={activityType} class="input" disabled={isLoading}>
        <option value="running">Corsa</option>
        <option value="cycling">Ciclismo</option>
      </select>
    </div>

    <div class="form-group">
      <label for="skill" class="label">Livello</label>
      <select id="skill" bind:value={skillLevel} class="input" disabled={isLoading}>
        <option value="beginner">Principiante (8 km/h)</option>
        <option value="intermediate">Intermedio (12 km/h)</option>
        <option value="advanced">Avanzato (16 km/h)</option>
      </select>
    </div>

    <div class="form-group">
      <label for="speed" class="label">Velocita (km/h) <span class="optional">opzionale</span></label>
      <input
        id="speed"
        type="number"
        bind:value={customSpeed}
        placeholder="default dal livello"
        class="input"
        step="0.1"
        min="1"
        disabled={isLoading}
      />
    </div>
  </fieldset>

  <!-- Route Section -->
  <fieldset class="fieldset">
    <legend class="legend">
      <span class="legend-icon">2</span> Percorso
    </legend>

    <div class="form-row">
      <div class="form-group">
        <label for="distance" class="label">Distanza max (km)</label>
        <input
          id="distance"
          type="number"
          bind:value={maxDistance}
          placeholder="es. 10"
          class="input"
          min="0.5"
          step="0.5"
          disabled={isLoading}
        />
      </div>

      <div class="form-group">
        <label for="duration" class="label">Durata max (min) <span class="optional">opz.</span></label>
        <input
          id="duration"
          type="number"
          bind:value={maxDuration}
          placeholder="es. 60"
          class="input"
          min="5"
          step="5"
          disabled={isLoading}
        />
      </div>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="direction" class="label">Direzione <span class="optional">opz.</span></label>
        <select id="direction" bind:value={direction} class="input" disabled={isLoading}>
          <option value="">Qualsiasi</option>
          <option value="N">Nord</option>
          <option value="NE">Nord-Est</option>
          <option value="E">Est</option>
          <option value="SE">Sud-Est</option>
          <option value="S">Sud</option>
          <option value="SW">Sud-Ovest</option>
          <option value="W">Ovest</option>
          <option value="NW">Nord-Ovest</option>
        </select>
      </div>

      <div class="form-group">
        <label for="terrain" class="label">Terreno <span class="optional">opz.</span></label>
        <select id="terrain" bind:value={terrain} class="input" disabled={isLoading}>
          <option value="">Misto (default)</option>
          <option value="flat">Pianeggiante</option>
          <option value="hilly">Collinare</option>
          <option value="mixed">Misto</option>
        </select>
      </div>
    </div>
  </fieldset>

  <button
    type="submit"
    class="btn-primary"
    disabled={isLoading}
  >
    {#if isLoading}
      <span class="spinner"></span>
      Generazione in corso...
    {:else}
      Genera Percorso
    {/if}
  </button>
</form>

<style>
  .route-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .fieldset {
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1rem;
    background: #0f172a;
  }

  .legend {
    font-size: 0.85rem;
    font-weight: 600;
    color: #94a3b8;
    padding: 0 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .legend-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #1e3a5f;
    color: #60a5fa;
    font-size: 0.7rem;
    font-weight: 700;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    flex: 1;
  }

  .form-row {
    display: flex;
    gap: 0.75rem;
  }

  .label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .optional {
    font-weight: 400;
    color: #64748b;
    text-transform: none;
    font-size: 0.7rem;
  }

  .input {
    width: 100%;
    padding: 0.55rem 0.75rem;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
    font-size: 0.875rem;
    transition: border-color 0.15s ease;
    outline: none;
  }

  .input:focus {
    border-color: #60a5fa;
    box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.15);
  }

  .input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  select.input {
    cursor: pointer;
    appearance: auto;
  }

  .btn-primary {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.7rem 1.5rem;
    background: linear-gradient(135deg, #2563eb, #7c3aed);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s ease, transform 0.1s ease;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
    transform: translateY(-1px);
  }

  .btn-primary:active:not(:disabled) {
    transform: translateY(0);
  }

  .btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
