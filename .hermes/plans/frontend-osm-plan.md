# Plan: Frontend con Mappa OSM per Routie

## Obiettivo
Aggiungere un frontend SPA che permette all'utente di generare percorsi
(corsa/cycling) visualizzati su mappa OpenStreetMap.

## Architettura

Frontend statico (HTML + CSS + JS vanilla) servito da FastAPI via `StaticFiles`.
Mappa con Leaflet.js + tile layer OpenStreetMap.
Nessuna dipendenza frontend aggiuntiva — CDN per Leaflet.

```
routie/
├── src/routie/
│   └── web/
│       ├── api.py              # + new frontend route
│       ├── schemas.py          # unchanged
│       └── static/             # NEW: frontend assets
│           ├── index.html       # SPA entry
│           ├── style.css        # Styles
│           ├── app.js           # App logic + Leaflet + API calls
│           └── favicon.ico      # Optional
├── tests/
│   └── web/
│       └── test_frontend.py    # NEW: integration tests
```

## Flusso utente

1. Apre `/` → caricato `static/index.html`
2. Browser chiede permesso geolocalizzazione → centro mappa su posizione
3. Profilo: nome, attività (running/cycling), skill level (beginner/intermediate/advanced)
   - Opzione "Quick start" con profilo temporaneo
4. Vincoli route: distanza max, durata max, direzione, terreno
5. Click "Genera Percorso" → POST /api/v1/routes/plan
6. Route visualizzata sulla mappa (polyline + waypoints)
7. Dettagli: distanza, dislivello, durata stimata, difficoltà

## Fasi implementazione (TDD)

### Fase 1 — Backend: static file serving
- [ ] Test: GET / → 200, content-type HTML
- [ ] Test: GET /static/... → 200 per assets
- [ ] Aggiungere mount StaticFiles + index.html redirect in api.py
- [ ] Modificare main.py o api.py per includere la frontend route
- [ ] Verificare test passano

### Fase 2 — Frontend: struttura HTML + CSS
- [ ] index.html: map container, form pannello laterale, dettagli route
- [ ] style.css: layout responsive, scuro, metriche moderne

### Fase 3 — Frontend: JavaScript + Leaflet
- [ ] Inizializzare mappa Leaflet con tile OSM
- [ ] Geolocation browser → centra mappa
- [ ] Form con campi: name, activity, skill, distance, duration, direction, terrain
- [ ] POST /api/v1/profiles → crea profilo
- [ ] POST /api/v1/routes/plan → genera route
- [ ] Disegnare waypoints come polyline sulla mappa
- [ ] Mostrare dettagli route in pannello
- [ ] Bottone "Nuovo percorso" per resettare

### Fase 4 — Test end-to-end
- [ ] Test frontend integration (httpx su pagine statiche)
- [ ] Test manuale: aprire browser, verificare flusso completo
