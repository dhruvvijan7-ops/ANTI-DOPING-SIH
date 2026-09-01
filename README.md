# CleanSport Intelligence — Anti-Doping Intelligence & Investigation Platform

**An investigative decision-support prototype for anti-doping intelligence analysts.**

CleanSport Intelligence helps anti-doping intelligence investigators analyze
information, detect unusual patterns, correlate signals across sources, identify
potentially relevant relationships, prioritize investigative leads, run investigations,
organize evidence, document findings and generate reports.

> **Important — what this system is, and is not.** This is an *investigative
> decision-support system*. It produces **signals and leads for human review** — it
> does **not** determine that an athlete is doping, does not produce "guilt scores",
> and never automatically confirms a rule violation. Every analytical output is a
> prioritized lead that a qualified investigator evaluates within the governed
> anti-doping process. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and
> [`docs/DOMAIN_VALIDATION.md`](docs/DOMAIN_VALIDATION.md).

---

## Table of contents

- [What it does](#what-it-does)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Setup (manual)](#setup-manual)
- [Running with Docker](#running-with-docker)
- [Database](#database)
- [Testing](#testing)
- [Documentation](#documentation)
- [Project status](#project-status)
- [Contributing](#contributing)
- [License](#license)

---

## What it does

From the investigator's perspective:

1. **Capture intelligence** from multiple sources (synthetic intake in this
   prototype) with source provenance, confidentiality and reliability metadata.
2. **Assess** each item for source reliability and information accuracy, following
   the WADA Admiralty-scale model (see `docs/DOMAIN_VALIDATION.md`).
3. **Detect signals** with a deterministic rule engine plus anomaly detection
   against a reference population (Isolation Forest), temporal correlation and
   relationship/network analysis.
4. **Prioritize** investigative leads with an explainable composite priority score,
   each backed by the evidence and rules that contributed.
5. **Alert** analysts, who triage, dismiss, escalate or open an investigation.
6. **Investigate** in a case workspace: lines of enquiry, evidence, tasks, notes,
   findings (inculpatory/exculpatory/neutral), timeline and relationship graph.
7. **Report** structured investigation reports without automatic guilt conclusions.

All analytical signals are *leads for human review*. The prototype runs entirely on
**synthetic data**; no real personal or sensitive information is used.

---

## Technology stack

### Backend — implemented

| Technology | Used for |
|---|---|
| Python 3.12+ | Backend runtime |
| FastAPI | REST API framework |
| Pydantic v2 / pydantic-settings | Validation + configuration |
| SQLAlchemy 2.x | ORM and data layer |
| Alembic | Database migrations |
| PostgreSQL 16 | Relational database |
| psycopg (v3) | PostgreSQL driver |
| python-jose + bcrypt | JWT auth + password hashing |
| uvicorn | ASGI server |
| pytest / httpx | Backend tests (+ `pytest-asyncio`) |

### Frontend — planned (not yet scaffolded)

| Technology | Planned use |
|---|---|
| React + TypeScript | Application UI |
| Vite | Build tool |
| Tailwind CSS + shadcn/ui | Styling + component library |
| TanStack Query | Server state |
| Zustand | Client state |
| React Hook Form + Zod | Forms + validation |
| Recharts | Charts |
| React Flow | Relationship graph |

### Intelligence / ML — planned (STAGE E)

scikit-learn (Isolation Forest), rule engine, temporal & cross-source correlation,
network analysis and a composite priority score. **Not yet implemented** — see
`docs/ARCHITECTURE.md` and `docs/PROJECT_STATUS.md` for the design and honest status.

### Infrastructure — implemented (backend/DB)

Docker Compose (PostgreSQL 16 + backend; frontend service defined but the `frontend/`
directory is not yet scaffolded), `.env.example` for configuration.

---

## Repository layout

```text
.
├── backend/                    # FastAPI backend (app, migrations, tests)
│   ├── app/
│   │   ├── api/                # Routes + dependencies
│   │   ├── core/               # Config, logging, exceptions
│   │   ├── db/                 # Session, seed
│   │   ├── models/             # SQLAlchemy models (identity, subjects,
│   │   │                       #   intelligence, events, relationships, scenarios)
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── security/           # Passwords, tokens, RBAC
│   │   └── services/           # Auth, audit services
│   ├── migrations/             # Alembic migrations
│   │   └── versions/
│   └── tests/
├── docs/                       # Living project documentation
├── RESEARCH FOR ANTI DOPING/   # 12-document specification package
├── docker-compose.yml
├── .env.example
└── .github/                    # CI workflow + issue/PR templates
```

`frontend/`, `ml/`, `scripts/` and `data/` directories will be added as their
respective stages are implemented.

---

## Quick start

### Prerequisites

- Git
- Docker (with `docker compose`) — recommended path
- OR Python 3.12+ + PostgreSQL 16 for manual setup

### Fastest path (Docker)

```bash
cp .env.example .env            # then adjust values if desired
docker compose up --build
```

- API: http://localhost:8000 (docs at http://localhost:8000/docs)
- Note: the `frontend` service requires the `frontend/` scaffold (not yet created).
  To run backend + database only: `docker compose up --build postgres backend`.

---

## Setup (manual)

### 1. Environment

```bash
cp .env.example .env
```

Edit `.env` as needed. Never commit `.env` (it is git-ignored).

### 2. Database

Start PostgreSQL (e.g. via Docker):

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
```

Apply migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Development RBAC roles and users are seeded automatically on startup when
`DEPLOY_INITIAL_USERS=true` and `APP_ENV=development` (see `.env.example`).

### 3. Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+psycopg://clean_sport:***@localhost:5432/clean_sport` |
| `JWT_SECRET_KEY` | JWT signing secret (change in real use) | `change-me-dev-only` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `1440` |
| `POSTGRES_*` | PostgreSQL container settings (compose) | `clean_sport` |
| `POSTGRES_HOST_PORT` | Host port for PostgreSQL (5432 is default; this machine uses 54320) | `5432` |
| `APP_ENV` / `DEBUG` | Runtime mode | `development` / `true` |
| `DEPLOY_INITIAL_USERS` | Seed RBAC users on startup | `true` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173` |

---

## Running with Docker

```bash
docker compose up --build
```

Services:

| Service | Container | Host port | Notes |
|---|---|---|---|
| `postgres` | `cleansport-postgres` | `${POSTGRES_HOST_PORT:-5432}` | 16-alpine |
| `backend` | `cleansport-backend` | `${BACKEND_PORT:-8000}` | runs `alembic upgrade head` then uvicorn |
| `frontend` | `cleansport-frontend` | `${FRONTEND_PORT:-8080}` | needs `frontend/` scaffold (not yet created) |

---

## Database

- Schema changes are version-controlled with **Alembic** migrations under
  `backend/migrations/versions/`.
- A fresh clone can be fully rebuilt with `alembic upgrade head` — no reliance on a
  developer's local database.
- A reproduction/seed flow is planned (deterministic synthetic generator, `seed-data`
  and `reset-data` operations).
- Current applied migration: `0001_identity_security` (users/roles/permissions/
  role_permissions/audit_events).

See [`docs/DATABASE.md`](docs/DATABASE.md) for initialization, migrations, seed and
reset procedures.

---

## Testing

Backend (pytest):

```bash
cd backend
pytest
```

Covered so far: authentication (`tests/test_auth.py`) and authorization
(`tests/test_authz.py`). See [`docs/TESTING.md`](docs/TESTING.md) for the full
test plan (backend, intelligence engine, and end-to-end workflow).

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, data flow, intelligence engine, explainability |
| [`docs/DATABASE.md`](docs/DATABASE.md) | DB initialization, migrations, seed/reset |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy and coverage plan |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | What works / in progress / planned; feature maturity |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Implementation decision log (D-001 … D-012) |
| [`docs/TRACEABILITY.md`](docs/TRACEABILITY.md) | Requirement → module → file → API → DB → test |
| [`docs/DOMAIN_VALIDATION.md`](docs/DOMAIN_VALIDATION.md) | 20 core concepts validated against WADA/ISTI/ISII/ITA |
| [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) | Stage-by-stage status matrix |
| [`docs/IMPLEMENTATION_BASELINE.md`](docs/IMPLEMENTATION_BASELINE.md) | Baseline snapshot |
| [`RESEARCH FOR ANTI DOPING/`](RESEARCH%20FOR%20ANTI%20DOPING/README.md) | 12-doc specification package |

---

## Project status

STAGE A (foundation: scaffolding, Docker, config, auth, RBAC, audit, migrations) is
implemented. STAGE B (domain model) models are written but the domain migration is
pending. Frontend, analytics, alerts, investigations, AI and reporting are planned.
For an honest, detailed status see [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## License

[MIT](LICENSE). This prototype uses synthetic data only and is not an affiliated,
endorsed or official product of WADA, NADA, ITA, or any anti-doping authority.