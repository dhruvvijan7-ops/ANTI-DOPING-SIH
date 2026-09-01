# Project Status

**Last updated:** 2026-09-01

Honest snapshot of what works, what is in progress, what is planned, known
limitations and technical debt. See [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md)
for the stage-by-stage feature matrix.

---

## Feature maturity classification

Used throughout: `UI ONLY`, `MOCKED`, `PARTIALLY FUNCTIONAL`, `FUNCTIONAL`,
`PRODUCTION READY`. Mocked or UI-only functionality is never presented as real.

---

## Completed (what actually works)

### Foundation (STAGE A) — FUNCTIONAL

- Repository scaffolding and Docker Compose for PostgreSQL + backend.
- `.env.example` configuration model (pydantic-settings).
- Alembic migration `0001_identity_security` (users, roles, permissions,
  role_permissions, audit_events) — applied and verifiable.
- Authentication: login/logout/me with JWT (python-jose) + bcrypt password hashing.
- RBAC with 4 roles (admin, investigator, intelligence analyst, viewer),
  server-validated permissions via dependency.
- Audit-log service.
- Backend tests for authentication and authorization.

### Domain Model (STAGE B) — PARTIALLY FUNCTIONAL (models written, migration pending)

- Subjects: `IntelligenceSource`-related actors (athlete, teams, organizations,
  support persons, providers, supplements).
- Intelligence: sources, reports, tags, source assessments.
- Events: testing, biological, whereabouts, travel, medical, supplement.
- Relationships: relationship types + entity relationships (graph source of truth).
- Scenarios: synthetic scenario registry.

### Docs — VERIFIED

- `DECISIONS.md` (D-001..D-012), `TRACEABILITY.md`, `IMPLEMENTATION_STATUS.md`,
  `IMPLEMENTATION_BASELINE.md`, `DOMAIN_VALIDATION.md`.
- Domain validation of 20 intelligence/investigation concepts against WADA/ISTI/ISII,
  ITA and NADA India primary sources (research pass 1).

---

## In progress

- **STAGE B completion:** autogenerate + apply the domain migration (including D-010
  Admiralty-scale enums), seed, and run the tests (fix test DB port 5432 → 54320).

---

## Planned

| Stage | Planned features |
|---|---|
| C — Synthetic data | Deterministic generator (500 athletes + events/reports/relationships), 9 known scenarios, `seed-data` / `reset-data` |
| D — Intelligence | Ingestion + validation + normalization, entity resolution/dedupe, intelligence inbox, athlete profile tabs |
| E — Analytics | Versioned rule engine, feature engineering, Isolation Forest anomaly + normalized score + explanation, temporal correlation (45d), cross-source correlation, network scoring, composite priority score `P=0.25R+0.20A+0.20C+0.15T+0.10N+0.10S`, analysis-run tracking |
| F — Alerts | Alert generation, alert center, triage (review/dismiss/escalate/request-analysis), false-positive handling, convert-to-case |
| G — Investigations | Case lifecycle, assignment, evidence, tasks, notes, findings (with D-011 evidential direction), lines of enquiry (D-012), timeline, relationship graph, workspace |
| H — AI assistant | Retrieval-grounded, deterministic fallback, no fabrication, human-in-the-loop |
| I — Reporting | Structured reports + preview, export best-effort, no automatic guilt conclusion |
| J — QA & docs | Unit/API/integration/e2e tests, analytical validation, API.md, DATA_DICTIONARY.md |

Frontend (React + TS + Vite + Tailwind + shadcn + TanStack Query + Zustand + RHF/Zod +
Recharts + React Flow) is planned to start with STAGE D.

---

## Known limitations

- **Frontend not yet scaffolded** — `docker-compose.yml` defines a `frontend` service
  whose build context (`./frontend`) does not exist yet; `docker compose up` for that
  service will fail until STAGE D.
- **Analytics/ML not implemented** — rule engine, Isolation Forest, correlation,
  network and priority scoring are designed but not coded. Do not treat
  `docs/ARCHITECTURE.md` analytics sections as implemented features.
- **No intelligence ingestion/entity resolution** yet (STAGE D).
- **No investigation case management** yet (STAGE G).
- **No AI assistant** yet (STAGE H). No LLM dependency is required by design (D-005).
- **No test coverage of the domain model** until STAGE B migration + tests are run.
- **Production anonymity/sharing explicitly out of scope** (D-006): the prototype does
  not provide real anonymous reporting infrastructure or cross-NADO sharing.

---

## Technical debt / deferred decisions

- `tests/conftest.py` still defaults `TEST_DATABASE_URL` to `localhost:5432`;
  must point at the current host port (54320) or an env override.
- Two Admiralty-scale information-rating ranges exist across WADA guideline editions
  (1–5 vs 1–6); D-010 selects 1–6 — must be crystalized as a single canonical table
  in `docs/DATA_DICTIONARY.md` when written.
- `2027 ISII/Code` are future frameworks (in force 2027-01-01); docs cite them as
  future-binding with the current ISTI analogue noted.
- Docker backend image pins `python:3.12-slim`; local dev runs Python 3.14 (D-007).