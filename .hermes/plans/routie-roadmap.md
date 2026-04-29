# Routie — Roadmap di Sviluppo

> **Goal:** App di route planning per runner e ciclisti (FastAPI + Svelte 5 + SQLite/PostgreSQL).
> **Stato:** MVP completato, CI/CD attivo, Docker configurato.

## Architettura

```
routie/
├── src/routie/
│   ├── domain/              # Entità, value objects, enums
│   ├── use_cases/           # Use cases (plan_route, profiles, routes)
│   ├── service/             # Provider astratti e concreti (mock, Valhalla)
│   ├── infrastructure/      # ORM (SQLAlchemy), repository, DB config
│   ├── web/                 # API routes (api.py), schemas (pydantic)
│   ├── main.py              # FastAPI app factory
│   └── config.py            # Config da ambiente
├── frontend/                # Svelte 5 + Vite
│   ├── src/                 # Componenti, store, services
│   └── dist/                # Build output (servito da FastAPI)
├── tests/                   # pytest (200+ test)
├── .github/workflows/
│   └── ci.yml              # Lint + mypy + test (3.12/3.13) + Docker build
├── Dockerfile               # Multi-stage (Node → Python 3.13-slim)
├── docker-compose.yml       # Profili: default, prod, tunnel, valhalla
├── config/
│   └── valhalla.json        # Configurazione Valhalla routing engine
└── .hermes/
    └── plans/               # Piani di sviluppo
```

## ✅ Completato

### Fase 0 — Setup & Fondamenta
- [x] Struttura progetto FastAPI con domain-driven design
- [x] Entità di dominio (Route, Waypoint, Profile, Direction, Difficulty, Surface, Terrain)
- [x] Value objects (Location, RouteStats, TimeOfDay)
- [x] Mock provider per route (generateRoute, getRouteById)
- [x] Use case `plan_route` con validazione parametri
- [x] Endpoint REST: `POST /api/v1/routes/plan`, `POST /api/v1/profiles`, `GET /api/v1/profiles/{id}`, `GET /api/v1/routes/{id}`
- [x] Storage SQLite via SQLAlchemy async
- [x] Frontend Svelte 5 + Leaflet + OSM (mappa interattiva)
- [x] 200+ test pytest passanti

### Fase 1 — CI/CD & Tooling
- [x] Configurazione ruff (Bugbear, Simplify, Pylint, Async, Pathlib)
- [x] Configurazione mypy strict mode
- [x] GitHub Actions: lint + type check + test matrix (3.12/3.13) + Docker build
- [x] Docker multi-stage (Node 20 build → Python 3.13-slim)
- [x] docker-compose con profili: default, prod (PostgreSQL), tunnel (ngrok)
- [x] PR #1 mergiata ✅ (feat/ci-cd → main)

### Operativo
- [x] Heartbeat Telegram ogni 6h (stato PR aperte)
- [x] `.gitignore` aggiornato
- [x] Polyline Encoding per MockProvider (encode + decode)

## 🚧 In Corso / Da Fare

### Priorità Alta

#### 1. Branch Protection su `main`
- [ ] Settings → Branches → Add rule per `main`
- [ ] Richiedere status checks: Lint & Type Check, Tests (3.12), Tests (3.13), Docker Build
- [ ] Richiedere review (opzionale: 1 approvazione)
- [ ] Bloccare push diretto su `main`

#### 2. CORS + Global Exception Handlers
- [ ] Configurare CORS middleware (FastAPI `CORSMiddleware`)
- [ ] Global exception handler per input non validi (422 → JSON leggibile)
- [ ] Handler per 404 custom
- [ ] Handler per 500 con logging strutturato
- [ ] Test coverage per gli handler

#### 3. Integrazione Valhalla Routing Engine 🚧
- [x] ValhallaRouteProvider (TDD: 22 test)
- [x] Chiamata POST HTTP a Valhalla `/route` API
- [x] Mapping costing profile (pedestrian/bicycle) da attività
- [x] Parsing risposta: distanza (km), tempo (s), elevazione, shape waypoint
- [x] Polyline encoding da shape coordinates
- [x] Config in Settings (VALHALLA_URL, provider selector)
- [x] Wiring in main.py con DI (mock/valhalla)
- [x] Docker Compose: servizio valhalla su porta 8002 (profile: valhalla)
- [x] Config Valhalla (pedestrian + bicycle profiles, elevation true)
- [x] Config file config/valhalla.json
- [ ] Download OSM data + primo import Valhalla (manuale)
- [ ] Test E2E con Valhalla reale in Docker
- [ ] Fallback automatico a mock se Valhalla non raggiungibile

### Priorità Media

#### 4. Endpoint Storico Route (`GET /api/v1/profiles/{id}/routes`)
- [ ] Query DB per recuperare route salvate per profilo
- [ ] Paginazione (offset/limit)
- [ ] Filtri per data, attività, distanza
- [ ] Test repository e API

### Priorità Bassa

#### 5. Miglioramenti UX Frontend
- [ ] Stato di caricamento durante generazione route
- [ ] Messaggi di errore user-friendly
- [ ] Salvataggio preferenze profilo
- [ ] PWA (service worker per offline)

#### 6. Documentazione
- [ ] README aggiornato con setup instructions
- [ ] API docs via FastAPI `/docs` e `/redoc`
- [ ] Esempi curl per ogni endpoint

## 📋 Regole del Progetto

- **Branch dedicati** per ogni feature: `feat/nome-feature`
- **PR verso `main`**, mai push diretto
- **Lingua**: italiano (codice doc/commit in inglese per convenzione)
- **Linting**: `ruff check src/ tests/` — 0 errori
- **Type checking**: `mypy src/` — strict mode
- **Test**: `pytest -v` — tutti passanti prima del commit
- **Docker**: `docker compose up` per test locale
- **Git push**: `--force-with-lease` mai `--force` nudo
- **Non-code changes** (docs, plan, gitignore): commit diretto su `main`
