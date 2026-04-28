# Routie — Architecture & Functional Specification

> **Status:** Design Document | **Version:** 0.1.0
> **Tagline:** Route planning for runners & cyclists, tailored to your skill.

---

## 1. Executive Summary

Routie is a web application that generates running/cycling routes tailored to a
user's skill profile and constraints (max distance, time, direction, terrain). It
starts as a PoC with a mock route provider and evolves toward integrations with
GraphHopper and Strava.

---

## 2. Functional Requirements

### FR-01 — User Profile
The user can define a profile with:
- `name` (string)
- `activity_type` — RUNNING | CYCLING
- `skill_level` — BEGINNER | INTERMEDIATE | ADVANCED
- `avg_speed_kmh` (float, optional — derived from skill_level if absent)
- `max_distance_km` (float, optional — preferred upper bound)
- `preferred_terrain` — FLAT | HILLY | MIXED (optional)
- `preferred_direction` — N | NE | E | SE | S | SW | W | NW | ANY (optional)

### FR-02 — Route Planning Request
The user can submit a route plan request with:
- `activity_type` (RUNNING | CYCLING) — required
- `max_distance_km` (float, optional)
- `max_duration_min` (int, optional)
- `preferred_direction` (Direction, optional)
- `terrain_type` (TerrainType, optional)
- `start_latitude` / `start_longitude` (float, optional — defaults to user's home)

### FR-03 — Route Generation
Given a request, the system returns a Route containing:
- `id` (UUID)
- `name` (auto-generated or user-supplied)
- `activity_type`
- `distance_km` (float)
- `elevation_gain_m` (float)
- `estimated_duration_min` (int)
- `difficulty_level` — EASY | MODERATE | HARD
- `polyline` (encoded polyline, optional — for map display)
- `waypoints` (list of Coordinates)
- `created_at` (datetime)

### FR-04 — Route Constraints
Generated routes MUST satisfy:
- distance ≤ `max_distance_km` (if specified)
- duration ≤ `max_duration_min` (if specified)
- route direction approximately matches `preferred_direction` (if specified)
- route terrain matches `preferred_terrain` (if specified)

### FR-05 — Provider Abstraction
Route providers (GraphHopper, Strava, Mock) implement a common interface so
the core business logic is decoupled from external services.

### FR-06 — REST API
All operations available via REST API (FastAPI):
- `POST /api/v1/profiles` — create profile
- `GET /api/v1/profiles/{id}` — get profile
- `POST /api/v1/routes/plan` — plan a route (takes profile_id + constraints)
- `GET /api/v1/routes/{id}` — get route details
- `GET /api/v1/health` — health check

---

## 3. Non-Functional Requirements

| # | Requirement | Detail |
|---|-------------|--------|
| NFR-01 | **Testability** | Every layer is unit-testable with fakes; no hard dependencies on I/O in domain/use-cases |
| NFR-02 | **Clean Code** | Functions ≤30 lines, one responsibility, guard clauses, no magic numbers |
| NFR-03 | **TDD First** | RED → GREEN → REFACTOR for every unit of production code |
| NFR-04 | **Extensibility** | New route providers added by implementing a single interface |
| NFR-05 | **Stateless API** | All state in DB; API servers are stateless (horizontal scaling ready) |

---

## 4. Architecture — Clean Architecture (Hexagonal)

```
┌─────────────────────────────────────────────────────────┐
│                   Web Layer (FastAPI)                     │
│  - REST endpoints                                        │
│  - Pydantic request/response schemas                     │
│  - Depends on: use_cases                                 │
├─────────────────────────────────────────────────────────┤
│                Application / Use Cases                    │
│  - PlanRouteUseCase                                      │
│  - ManageProfileUseCase                                  │
│  - Depends on: domain interfaces (Ports)                 │
├─────────────────────────────────────────────────────────┤
│                    Service Layer                          │
│  - RoutePlannerService (coordinates providers)           │
│  - Provider interface (Port)                             │
├─────────────────────────────────────────────────────────┤
│                    Domain Layer                           │
│  - Entities: UserProfile, Route, RoutePlanRequest        │
│  - Value Objects: Coordinates, Distance, Duration, ...   │
│  - Enums: ActivityType, SkillLevel, TerrainType, ...     │
│  - Pure Python — NO external dependencies                │
├─────────────────────────────────────────────────────────┤
│                 Infrastructure Layer                      │
│  - Repository implementations (SQLite via SQLAlchemy)     │
│  - In-memory repository (for tests)                      │
│  - Provider implementations (MockProvider, GraphHopper)  │
│  - Database setup / migrations                           │
└─────────────────────────────────────────────────────────┘
```

### Dependency Rule
**Dependencies point inward.** Domain knows nothing about web, services, or
infrastructure. Use cases depend on domain + ports (interfaces). Infrastructure
and web depend on use cases + ports.

---

## 5. Data Model (Domain)

```
┌──────────────────────┐       ┌──────────────────────────┐
│    UserProfile        │       │   RoutePlanRequest       │
├──────────────────────┤       ├──────────────────────────┤
│ + id: UUID           │       │ + id: UUID               │
│ + name: str          │       │ + activity_type: Activity │
│ + activity_type: Act │       │ + max_distance_km: float? │
│ + skill_level: Skill │       │ + max_duration_min: int? │
│ + avg_speed_kmh: flo │       │ + preferred_direction: Di│
│ + max_distance_km: f │       │ + terrain_type: Terrain? │
│ + preferred_terrain: │       │ + start_lat/lon: float?  │
│ + preferred_direction│       └──────────┬───────────────┘
│ + home_lat/lon: floa │                  │ produces
│ + created_at: dateti │                  ▼
└──────────────────────┘       ┌──────────────────────────┐
                               │         Route             │
                               ├──────────────────────────┤
                               │ + id: UUID               │
                               │ + name: str               │
                               │ + activity_type: Activity │
                               │ + distance_km: float      │
                               │ + elevation_gain_m: float │
                               │ + estimated_duration_min: │
                               │ + difficulty: Difficulty  │
                               │ + polyline: str?          │
                               │ + waypoints: list[Coord]  │
                               │ + created_at: datetime    │
                               └──────────────────────────┘
```

---

## 6. Route Provider Interface (Port)

```python
class RouteProvider(ABC):
    @abstractmethod
    async def plan_route(
        self,
        request: RoutePlanRequest,
        profile: UserProfile,
    ) -> Route:
        ...
```

Implementations:
- **MockProvider** — Generates plausible routes algorithmically (no API call).
  Used for development + tests.
- **GraphHopperProvider** — Real route via GraphHopper routing API.
- **StravaProvider** — Uses Strava API routes/segments.

---

## 7. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.13 | Rich ecosystem, excellent for clean code & testing |
| **Web framework** | FastAPI | Async, Pydantic validation, auto-docs |
| **ORM** | SQLAlchemy 2.0 | Mature, well-tested, async support |
| **Database** | SQLite (dev) → PostgreSQL (prod) | Zero-config for PoC |
| **Testing** | pytest + pytest-asyncio | Standard Python test framework |
| **Validation** | Pydantic v2 | Validation + serialization |
| **Async HTTP** | httpx | For future provider integrations |
| **CI** | GitHub Actions (future) | — |

---

## 8. Development Phases

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| **P1 — Domain & Core** | Value objects, entities, enums | Tests + domain module |
| **P2 — Use Cases** | PlanRouteUseCase, ManageProfileUseCase | Tests + application logic |
| **P3 — Mock Provider** | MockRouteProvider (algorithmic routes) | Working route generation |
| **P4 — Infrastructure** | In-memory repo, SQLite repo, unit of work | Persistence layer |
| **P5 — Web API** | FastAPI endpoints, error handling, docs | Runnable API server |
| **P6 — Integration** | GraphHopperProvider or StravaProvider | Real route generation |

---

## 9. Project Structure

```
routie/
├── pyproject.toml
├── README.md
├── src/
│   └── routie/
│       ├── __init__.py
│       ├── main.py                  # FastAPI entry point
│       ├── config.py                # Configuration
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── enums.py             # ActivityType, SkillLevel, etc.
│       │   ├── value_objects.py     # Coordinates, Distance, etc.
│       │   └── models.py            # UserProfile, Route, RoutePlanRequest
│       ├── use_cases/
│       │   ├── __init__.py
│       │   ├── plan_route.py        # PlanRouteUseCase
│       │   └── manage_profile.py    # ManageProfileUseCase
│       ├── service/
│       │   ├── __init__.py
│       │   ├── route_planner.py     # RoutePlannerService
│       │   └── providers/
│       │       ├── __init__.py
│       │       ├── base.py          # RouteProvider ABC
│       │       └── mock.py          # MockRouteProvider
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── database.py          # SQLAlchemy async engine/session
│       │   ├── repository.py        # SQLAlchemy repositories
│       │   └── in_memory_repo.py    # In-memory repos (test/dev)
│       └── web/
│           ├── __init__.py
│           ├── api.py               # FastAPI router
│           └── schemas.py           # Pydantic request/response schemas
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures
│   ├── domain/
│   │   ├── test_enums.py
│   │   ├── test_value_objects.py
│   │   └── test_models.py
│   ├── use_cases/
│   │   ├── test_plan_route.py
│   │   └── test_manage_profile.py
│   ├── service/
│   │   └── test_route_planner.py
│   └── web/
│       └── test_api.py
└── docs/
    └── architecture.md              # This file
```

---

## 10. Testing Strategy

| Level | Scope | What We Test |
|-------|-------|-------------|
| **Unit (domain)** | No mocks | Value object invariants, entity creation, enum validation |
| **Unit (use case)** | Fake repos | Business rules: constraints, profile matching |
| **Unit (service)** | Mock providers | Provider selection, fallback logic |
| **Integration (web)** | TestClient | HTTP status codes, schema validation, error responses |
| **Smoke** | Running server | Health check, basic flow |

Tests are written BEFORE production code (TDD). Every test must fail RED before
turning GREEN.

---

## 11. Route Planning Algorithm (MockProvider)

The MockProvider generates a route using a simple algorithm:

1. Choose a random direction based on preferred_direction
2. Walk in that direction, generating waypoints at random offsets
3. Ensure total distance ≤ max_distance_km
4. Calculate elevation_gain as a function of distance × terrain_factor
5. Estimate duration from distance / avg_speed
6. Determine difficulty from distance × elevation_factor
7. Encode polyline from waypoints

This is intentionally simple for the PoC. Real route planning using GraphHopper
will follow road networks.

---

## 12. Error Handling

| Condition | HTTP Status | Error Code |
|-----------|-------------|------------|
| Profile not found | 404 | PROFILE_NOT_FOUND |
| Route not found | 404 | ROUTE_NOT_FOUND |
| Invalid input | 422 | VALIDATION_ERROR |
| No suitable route found | 404 | NO_ROUTE_FOUND |
| Provider unavailable | 503 | PROVIDER_UNAVAILABLE |

All errors return: `{"error": {"code": "STRING_CODE", "message": "human text"}}`
