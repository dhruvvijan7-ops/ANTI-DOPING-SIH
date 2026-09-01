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
| Repository scaffolding | NOT_STARTED | - | - | - | - | greenfield |
| Docker Compose (frontend/backend/postgres) | NOT_STARTED | - | - | - | - | |
| Config via env / `.env.example` | NOT_STARTED | - | - | - | - | |
| Alembic migrations + PostgreSQL | NOT_STARTED | - | - | - | - | |
| Authentication (login/logout/me) | NOT_STARTED | - | - | - | - | |
| RBAC (4 roles, backend-enforced) | NOT_STARTED | - | - | - | - | |
| Audit-log service | NOT_STARTED | - | - | - | - | |
| React app shell + routing + protected routes | NOT_STARTED | - | - | - | - | |

## Domain Model (STAGE B)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Identity (users/roles/permissions) | NOT_STARTED | - | - | - | - | D-001 merged schema |
| Subjects (athletes/support/teams/orgs/providers) | NOT_STARTED | - | - | - | - | |
| Intelligence (sources/reports/assessments/tags/relationships) | PARTIAL | - | - | - | - | D-010 Admiralty enums pending in migration |
| Events (testing/biological/whereabouts/travel/medical/supplement) | NOT_STARTED | - | - | - | - | |
| Relationships (entity_relationships/relationship_types) | NOT_STARTED | - | - | - | - | |
| Analytics stores (indicators/runs/feature_snapshots/anomaly/rule/correlation/network/priority/model/rule versions) | NOT_STARTED | - | - | - | - | |
| Alerts (alerts/alert_signals/alert_reviews) | NOT_STARTED | - | - | - | - | |
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
| Rule engine (versioned) | NOT_STARTED | - | - | - | - | |
| Feature engineering | NOT_STARTED | - | - | - | - | |
| Isolation Forest + normalized score + explanation | NOT_STARTED | - | - | - | - | |
| Temporal correlation (45d) | NOT_STARTED | - | - | - | - | |
| Cross-source correlation | NOT_STARTED | - | - | - | - | |
| Network scoring + graph | NOT_STARTED | - | - | - | - | |
| Composite priority score + decomposition | NOT_STARTED | - | - | - | - | |
| Analysis run tracking/reproducibility | NOT_STARTED | - | - | - | - | |

## Alerts (STAGE F)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Alert generation (thresholds/correlation/rule/network) | NOT_STARTED | - | - | - | - | |
| Alert center + detail + score breakdown | NOT_STARTED | - | - | - | - | |
| Triage (review/dismiss/escalate/request-analysis) | NOT_STARTED | - | - | - | - | |
| False-positive handling | NOT_STARTED | - | - | - | - | |
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
| Unit tests (rules/ML/correlation/network/priority) | NOT_STARTED | - | - | - | - | |
| API + authz tests | NOT_STARTED | - | - | - | - | |
| Integration tests (DB→repo→service→API) | NOT_STARTED | - | - | - | - | |
| End-to-end workflow test | NOT_STARTED | - | - | - | - | |
| Analytical validation (scenario separation) | NOT_STARTED | - | - | - | - | |
| `docs/API.md` | NOT_STARTED | - | - | - | - | |
| `docs/DATA_DICTIONARY.md` | NOT_STARTED | - | - | - | - | |
| `docs/DOMAIN_VALIDATION.md` | VERIFIED | - | - | - | - | 20 concepts validated vs WADA/ISTI/ISII/ITA; D-010..D-012 raised |
| Dashboard metrics from backend | NOT_STARTED | - | - | - | - | |
| Error/empty/loading states everywhere | NOT_STARTED | - | - | - | - | |
| Demo workflow (directive §66) verified | NOT_STARTED | - | - | - | - | |

---

*Updated at the end of each stage. A feature is not complete merely because code exists.*
