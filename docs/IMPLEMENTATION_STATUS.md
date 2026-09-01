# Implementation Status

Tracks feature completeness. Status values: `NOT_STARTED`, `IN_PROGRESS`, `IMPLEMENTED`,
`TESTED`, `VERIFIED`.

A feature is complete only when backend + database + API + frontend + authorization +
loading/error/empty states + tests + documentation all exist and work against seeded
synthetic data (directive §65, §68).

---

## Legend

- **NOT_STARTED** — no work done
- **IN_PROGRESS** — partially implemented
- **IMPLEMENTED** — code exists end-to-end but not yet verified/tested
- **TESTED** — automated tests pass
- **VERIFIED** — demonstrated against seeded data + manual workflow confirmed

---

## Foundation (STAGE A)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Repository scaffolding | TESTED | IMPLEMENTED | - | - | - | README, CONTRIBUTING, LICENSE, CI |
| Docker Compose (frontend/backend/postgres) | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | Postgres 16, backend, frontend |
| Config via env / `.env.example` | TESTED | IMPLEMENTED | - | - | - | pydantic-settings |
| Alembic migrations + PostgreSQL | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | Migrations 0001, 0002 (38 tables) |
| Authentication (login/logout/me) | TESTED | IMPLEMENTED | - | IMPLEMENTED | 9 tests | JWT + bcrypt, 401 on invalid |
| RBAC (4 roles, backend-enforced) | TESTED | IMPLEMENTED | - | IMPLEMENTED | 11 tests | admin/investigator/analyst/viewer |
| Audit-log service | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | Middleware + ORM model |
| React app shell + routing + protected routes | NOT_STARTED | - | - | - | - | |

## Domain Model (STAGE B)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Identity (users/roles/permissions) | TESTED | IMPLEMENTED | - | IMPLEMENTED | 9 tests | Users, roles, permissions, role_permissions |
| Subjects (athletes/support/teams/orgs/providers) | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | 6 subject models |
| Intelligence (sources/reports/assessments/tags/relationships) | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | D-010 Admiralty enums via CHECK |
| Events (testing/biological/whereabouts/travel/medical/supplement) | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | 6 event models, each with source_id FK |
| Relationships (entity_relationships/relationship_types) | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | Generic relationship graph |
| Analytics stores (indicators/runs/feature_snapshots/anomaly/rule/correlation/network/priority,model/rule versions) | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | 11 ORM tables in analytics.py |
| Alerts (alerts/alert_signals/alert_reviews) | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | Full traceability alert→signals→features |
| Investigations (cases/assignments/notes/tasks/actions/findings) | NOT_STARTED | - | - | - | - | D-011 findings direction, D-012 lines of enquiry |
| Evidence (items/links/metadata) | NOT_STARTED | - | - | - | - | |
| Reporting (reports/report_versions) + outcomes | NOT_STARTED | - | - | - | - | |

## Synthetic Data (STAGE C)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Deterministic generator (500 athletes, events, reports, relationships) | NOT_STARTED | - | - | - | - | |
| 9 known scenarios (Normal..Unreliable source) | NOT_STARTED | - | - | - | - | |
| `seed-data` / `reset-data` operations | NOT_STARTED | - | - | - | - | |

## Intelligence (STAGE D)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Ingestion + validation + normalization | NOT_STARTED | - | - | - | - | |
| Entity resolution + dedupe | NOT_STARTED | - | - | - | - | |
| Intelligence inbox (filters/sort) | NOT_STARTED | - | - | - | - | |
| Athlete profile tabs | NOT_STARTED | - | - | - | - | |

## Analytics (STAGE E)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Rule engine (versioned) | TESTED | IMPLEMENTED | - | IMPLEMENTED | 7 tests | 9 rules (RULES-001..009), severity/weight |
| Feature engineering | TESTED | IMPLEMENTED | - | IMPLEMENTED | 11 tests | 17 versioned features (v2) |
| Isolation Forest + normalized score + explanation | TESTED | IMPLEMENTED | - | IMPLEMENTED | 5 tests | IF: n_estimators=200, contamination=0.05, reproducible |
| Temporal correlation (45d) | TESTED | IMPLEMENTED | - | IMPLEMENTED | 8 tests | Burst detection, category x time |
| Cross-source correlation | TESTED | IMPLEMENTED | - | IMPLEMENTED | 8 tests | 90d window, deduplication by key |
| Network scoring + graph | TESTED | IMPLEMENTED | - | IMPLEMENTED | 5 tests | Degree, diversity, connected priority |
| Composite priority score + decomposition | TESTED | IMPLEMENTED | - | IMPLEMENTED | 7 tests | 5-level classification, deterministic explanation |
| Analysis run tracking/reproducibility | TESTED | IMPLEMENTED | - | IMPLEMENTED | 3 API tests | Full pipeline orchestration, 2-pass network |

## Alerts (STAGE F)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Alert generation (thresholds/correlation/rule/network) | TESTED | IMPLEMENTED | - | IMPLEMENTED | API tests | Triggered when priority >= threshold |
| Alert center + detail + score breakdown | TESTED | IMPLEMENTED | - | IMPLEMENTED | API tests | Traceability: alert→signals→features→events |
| Triage (review/dismiss/escalate/request-analysis) | TESTED | IMPLEMENTED | - | IMPLEMENTED | API tests | PATCH /alerts/{id}/status |
| False-positive handling | TESTED | IMPLEMENTED | - | IMPLEMENTED | 5 tests | Strong single-signal stays <70, not CRITICAL |
| Convert to case | NOT_STARTED | - | - | - | - | |

## Investigations (STAGE G)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Case creation + lifecycle | NOT_STARTED | - | - | - | - | |
| Assignment | NOT_STARTED | - | - | - | - | |
| Evidence management | NOT_STARTED | - | - | - | - | |
| Tasks | NOT_STARTED | - | - | - | - | |
| Notes (audited) | NOT_STARTED | - | - | - | - | |
| Findings | NOT_STARTED | - | - | - | - | |
| Timeline | NOT_STARTED | - | - | - | - | |
| Relationship graph (React Flow) | NOT_STARTED | - | - | - | - | |
| Investigation workspace page | NOT_STARTED | - | - | - | - | |

## AI (STAGE H)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Retrieval-grounded assistant | NOT_STARTED | - | - | - | - | |
| Summaries / explanations / suggested questions | NOT_STARTED | - | - | - | - | |
| Deterministic fallback | NOT_STARTED | - | - | - | - | |

## Reporting (STAGE I)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Report generation (structured sections) | NOT_STARTED | - | - | - | - | |
| Report preview | NOT_STARTED | - | - | - | - | |
| Export (where feasible) | NOT_STARTED | - | - | - | - | |

## QA & Docs (STAGE J)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Unit tests (rules/ML/correlation/network/priority) | TESTED | - | - | - | 41 tests | features(11), rules(7), anomaly(5), correlation(8), network(5), priority(7) |
| API + authz tests | TESTED | - | - | - | 20 tests | auth(9), authz(11) |
| Integration tests (DB→repo→service→API) | TESTED | - | - | - | 3 tests | Full analysis run + traceability + unauth |
| End-to-end workflow test | TESTED | - | - | - | 5 tests | Scenario validation (network/multi-source/false-positive) |
| Analytical validation (scenario separation) | TESTED | - | - | - | 5 tests | network>normal, multi>normal, FP<70 |
| `docs/API.md` | NOT_STARTED | - | - | - | - | |
| `docs/DATA_DICTIONARY.md` | NOT_STARTED | - | - | - | - | |
| `docs/DOMAIN_VALIDATION.md` | VERIFIED | - | - | - | - | 20 concepts validated vs WADA/ISTI/ISII/ITA; D-010..D-012 raised |
| Dashboard metrics from backend | NOT_STARTED | - | - | - | - | |
| Error/empty/loading states everywhere | NOT_STARTED | - | - | - | - | |
| Demo workflow (directive §66) verified | NOT_STARTED | - | - | - | - | |

---

*Updated at the end of each stage. A feature is not complete merely because code exists.*
