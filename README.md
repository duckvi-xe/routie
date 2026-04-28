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

# Start server
uvicorn routie.main:app --reload

# Open docs
open http://localhost:8000/docs
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

## License

MIT
