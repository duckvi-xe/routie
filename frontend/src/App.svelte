<script>
  import MapView from "./components/MapView.svelte";
  import RouteForm from "./components/RouteForm.svelte";
  import RouteDetails from "./components/RouteDetails.svelte";

  let profileId = $state(null);
  let profileName = $state("");
  let routeResult = $state(null);
  let waypoints = $state([]);
  let loading = $state(false);
  let error = $state("");

  function handleProfileCreated(ev) {
    profileId = ev.detail.id;
    profileName = ev.detail.name;
  }

  function handleRouteGenerated(ev) {
    routeResult = ev.detail;
    waypoints = ev.detail.waypoints || [];
    error = "";
  }

  function handleError(ev) {
    error = ev.detail;
    routeResult = null;
    waypoints = [];
  }

  function handleReset() {
    routeResult = null;
    waypoints = [];
    error = "";
  }
</script>

<div class="app-container">
  <aside class="sidebar">
    <header class="sidebar-header">
      <h1>Routie</h1>
      <p class="tagline">Route planning for runners & cyclists</p>
    </header>

    <div class="sidebar-content">
      {#if error}
        <div class="error-banner" role="alert">
          <span class="error-icon">!</span>
          <span>{error}</span>
        </div>
      {/if}

      <RouteForm
        {profileId}
        {loading}
        on:profileCreated={handleProfileCreated}
        on:routeGenerated={handleRouteGenerated}
        on:error={handleError}
        on:reset={handleReset}
      />

      {#if routeResult}
        <RouteDetails route={routeResult} onReset={handleReset} />
      {/if}
    </div>
  </aside>

  <main class="map-area">
    <MapView {waypoints} />
  </main>
</div>

<style>
  :global(*) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  :global(body) {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
      Ubuntu, Cantarell, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    overflow: hidden;
    height: 100vh;
  }

  .app-container {
    display: flex;
    height: 100vh;
    width: 100vw;
  }

  .sidebar {
    width: 380px;
    min-width: 380px;
    background: #1e293b;
    border-right: 1px solid #334155;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .sidebar-header {
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #334155;
    background: #0f172a;
  }

  .sidebar-header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .tagline {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 0.25rem;
  }

  .sidebar-content {
    padding: 1rem 1.5rem 2rem;
    flex: 1;
    overflow-y: auto;
  }

  .map-area {
    flex: 1;
    position: relative;
  }

  .error-banner {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: #7f1d1d;
    border: 1px solid #dc2626;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
    color: #fca5a5;
  }

  .error-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #dc2626;
    color: #fff;
    font-weight: 700;
    font-size: 0.75rem;
    flex-shrink: 0;
  }
</style>
