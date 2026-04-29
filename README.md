# Routie 🏃🚴

Route planning for runners and cyclists — tailored to your skill level.

## Architecture

Clean Architecture (Hexagonal) with 5 layers:

```
Domain (pure Python)  →  Use Cases  →  Services  →  Infrastructure  →  Web (FastAPI)
```

## Quick Start

```bash
# Create virtual env & install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,web]"

# Run tests
pytest tests/ -q

# Start server (in-memory — data reset on restart)
uvicorn routie.main:app --reload

# Open docs
open http://localhost:8000/docs
```

## Persistence

By default, Routie runs with **in-memory repositories** — data is lost when
the server restarts. For persistent storage, enable the SQL backend:

```bash
# Install DB dependencies
pip install -e ".[db]"

# Start with SQLite persistence
USE_DB=true uvicorn routie.main:app --reload

# Or use PostgreSQL
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/routie" \
  USE_DB=true uvicorn routie.main:app --reload
```

Full install (dev tools + web + db):

```bash
pip install -e ".[all]"
```

## Docker

### Local (SQLite persistence)

```bash
# Build and start
docker compose up --build

# Open http://localhost:8000
```

### Production-like (PostgreSQL)

```bash
docker compose --profile prod up --build
```

### With ngrok tunnel (expose to internet)

```bash
# 1. Copy and edit env file
cp .env.example .env
# Set NGROK_AUTHTOKEN (get one at https://ngrok.com)

# 2. Start with tunnel
docker compose --profile tunnel up --build

# Combined with PostgreSQL:
docker compose --profile prod --profile tunnel up --build
```

The ngrok URL is printed in the ngrok container logs:

```bash
docker compose logs ngrok
```

### Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build — Svelte frontend + FastAPI backend |
| `docker-compose.yml` | Services: backend, PostgreSQL (opt), ngrok (opt) |
| `.env.example` | Template for environment variables |

## Valhalla Routing Engine

Routie uses **Valhalla** as its primary routing engine — a self-hosted, open-source
routing service from Mapbox. It supports pedestrian (running) and bicycle routing
with elevation-aware costing.

### Architecture

```
User  →  Routie (FastAPI)  →  Valhalla (Docker)
  |                            |
  | POST /api/v1/routes/plan   | POST /route JSON API
  | ROUTE_PROVIDER=valhalla    | Port 8002
```

### Quick Start (Andorra — 5 min)

```bash
# Download OSM data, start Valhalla AND Routie on the same Docker network
./scripts/setup_valhalla.sh andorra

# Plan a route!
curl -X POST http://localhost:8000/api/v1/routes/plan \
  -H "Content-Type: application/json" \
  -d '{"profile_id":"<UUID>","activity_type":"running","max_distance_km":10.0,"start_location":{"lat":42.50,"lon":1.52}}'
```

### Production Setup (Italy, larger region)

```bash
# Download Italy (~1.5 GB PBF) and start Valhalla (first import: 10-30 min)
# The script also starts Routie backend on the same Docker network
./scripts/setup_valhalla.sh italy

# Monitor the import
docker compose logs --tail=50 -f valhalla
```

### Multiple Regions

```bash
./scripts/setup_valhalla.sh "italy,switzerland"
```

### Manual Control

```bash
# Start only Valhalla (no build step — uses cached tiles)
docker compose --profile valhalla up -d

# Force rebuild tiles from scratch (e.g., after updating OSM data)
VALHALLA_REBUILD=true docker compose --profile valhalla up -d valhalla

# Combined with Routie
ROUTE_PROVIDER=valhalla VALHALLA_REBUILD=true \
  docker compose --profile valhalla up -d backend valhalla

# Stop everything
docker compose --profile valhalla down
```

### Test Valhalla Directly

```bash
curl -X POST http://localhost:8002/route \
  -H "Content-Type: application/json" \
  -d '{
    "costing": "pedestrian",
    "locations": [
      {"lat": 41.89, "lon": 12.49},
      {"lat": 41.90, "lon": 12.50}
    ]
  }'
```

### Configuration

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `ROUTE_PROVIDER` | `mock` | `"mock"` for dev, `"valhalla"` for real routing |
| `VALHALLA_URL` | `http://valhalla:8002` | Valhalla endpoint (Docker internal DNS) |
| `VALHALLA_THREADS` | `2` | CPU threads for Valhalla tile building |
| `VALHALLA_REBUILD` | `false` | Force rebuild routing tiles on startup |

Valhalla costing profiles are configured in [`config/valhalla.json`](config/valhalla.json).

### How It Works

1. The [`setup_valhalla.sh`](scripts/setup_valhalla.sh) script downloads an OSM
   `.osm.pbf` extract from [Geofabrik](https://download.geofabrik.de).
2. Files are placed in `custom_files/`, which is mounted into the Valhalla
   container at `/custom_files/`.
3. On first run, `ghcr.io/gis-ops/docker-valhalla` builds the routing tile
   database — this is the slow step (5-30 min depending on region).
4. Once built, tiles are cached in the `valhalla-tiles` Docker volume.
5. Subsequent starts skip the build (unless `VALHALLA_REBUILD=true`).

### Fallback Behaviour

If Valhalla is unreachable, Routie falls back to the mock provider
(algorithmic routing) so the app stays functional during development.

### Networks & DNS

`setup_valhalla.sh` starts both Valhalla and the backend under the same
Docker Compose project, so they share a network and the hostname `valhalla`
resolves via Docker DNS.

If you start the backend **outside** Docker (e.g. `uvicorn` directly):

```bash
# Valhalla is in Docker, backend is on the host
VALHALLA_URL=http://localhost:8002 ROUTE_PROVIDER=valhalla uvicorn routie.main:app --reload
```

| Setup | `VALHALLA_URL` |
|-------|----------------|
| Backend in Docker Compose (default) | `http://valhalla:8002` (Docker DNS) |
| Backend on host / outside Docker | `http://localhost:8002` (host port) |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/profiles` | Create user profile |
| GET | `/api/v1/profiles/{id}` | Get profile |
| PATCH | `/api/v1/profiles/{id}` | Update profile |
| DELETE | `/api/v1/profiles/{id}` | Delete profile |
| POST | `/api/v1/routes/plan` | Plan a route |
| GET | `/api/v1/routes/{id}` | Get route details |

## Example

```bash
# Create profile
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "Content-Type: application/json" \
  -d '{"name":"Andrea","activity_type":"running","skill_level":"intermediate"}'

# Plan a route
curl -X POST http://localhost:8000/api/v1/routes/plan \
  -H "Content-Type: application/json" \
  -d '{"profile_id":"<UUID from above>","activity_type":"running","max_distance_km":10.0}'
```

## Development

**TDD First.** Every feature starts with a failing test.

```bash
# Run all tests
pytest tests/ -q

# Run specific test
pytest tests/domain/test_enums.py -v

# Coverage
pytest tests/ --cov=routie
```

### Project structure

```
src/routie/
├── domain/                # Pure Python domain layer
│   ├── enums.py           # ActivityType, SkillLevel, Direction, etc.
│   ├── value_objects.py   # Coordinates, Distance, Duration
│   └── models.py          # UserProfile, Route, RoutePlanRequest
├── use_cases/             # Application business rules
│   ├── plan_route.py      # PlanRouteUseCase
│   └── manage_profile.py  # ManageProfileUseCase
├── service/               # Service layer
│   └── providers/
│       ├── base.py        # RouteProvider ABC
│       └── mock.py        # MockRouteProvider (algorithmic)
├── infrastructure/        # Persistence & adapters
│   ├── database.py        # Async SQLAlchemy engine + session factory
│   ├── orm.py             # SQLAlchemy ORM models
│   ├── repository.py      # SQLAlchemy-backed repositories
│   └── in_memory_repo.py  # In-memory repos (dev/test)
├── web/                   # FastAPI layer
│   ├── api.py             # REST endpoints
│   └── schemas.py         # Pydantic request/response schemas
├── config.py              # Settings from env vars
└── main.py                # App factory + entry point
```

### Configuration

All settings are controlled via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `info` | Logging level |
| `CORS_ORIGINS` | `*` | CORS allowed origins |
| `DATABASE_URL` | `sqlite+aiosqlite:///routie.db` | Database connection string |
| `USE_DB` | `false` | Enable SQL persistence |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Testing | pytest + pytest-asyncio |
| Validation | Pydantic v2 |
| Async HTTP | httpx |
| Frontend | Svelte 5 + Leaflet / OpenStreetMap |

## License

MIT
