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
