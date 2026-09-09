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
| Docker Compose (frontend/backend/postgres) | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | - | Postgres 16; services `verity-postgres`/`verity-backend`/`verity-frontend`; nginx `/api` proxy + SPA fallback; same-origin login verified on :8080 |
| Config via env / `.env.example` | TESTED | IMPLEMENTED | - | - | - | pydantic-settings |
| Alembic migrations + PostgreSQL | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | Migrations 0001, 0002, 0003 (evidence integrity/assignment) |
| Authentication (login/logout/me) | TESTED | IMPLEMENTED | - | IMPLEMENTED | 9 tests | JWT + bcrypt, 401 on invalid |
| RBAC (4 roles, backend-enforced) | TESTED | IMPLEMENTED | - | IMPLEMENTED | 11 tests | admin/investigator/analyst/viewer |
| Audit-log service | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | Middleware + ORM model |
| React app shell + routing + protected routes | VERIFIED | IMPLEMENTED | IMPLEMENTED | - | 42 frontend tests | `React.lazy` route split, `RequireAuth`, RBAC-filtered nav, skip link |

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
| Investigations (cases/assignments/notes/tasks/actions/findings) | TESTED | IMPLEMENTED | - | IMPLEMENTED | 4 API tests | D-011 findings direction, D-012 lines of enquiry; CRUD + close + audit trail |
| Evidence (items/links/metadata) | TESTED | IMPLEMENTED | - | IMPLEMENTED | API tests | Evidence items per case with types/classification |
| Reporting (reports/report_versions) + outcomes | TESTED | IMPLEMENTED | - | IMPLEMENTED | API tests | Versioned sections; publish→FINAL; edit supersedes |

## Synthetic Data (STAGE C)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Deterministic generator (14 athletes, events, reports, relationships) | TESTED | IMPLEMENTED | - | IMPLEMENTED | runtime | `app/data/generators.py`, per-key PRNG; same seed+as_of reproduces exactly |
| Scenario registry (7 known scenarios, normal..false positive) | TESTED | IMPLEMENTED | - | IMPLEMENTED | runtime | `app/data/registry.py`, stable refs + ground-truth labels |
| `populate` / `reset` / `list` operations | TESTED | IMPLEMENTED | - | IMPLEMENTED | runtime | `app/data/populate.py` + `app/data/cli.py`; scoped `TRUNCATE ... CASCADE` |
| Full pipeline execution per scenario | TESTED | IMPLEMENTED | - | IMPLEMENTED | runtime | Feed real `run_analysis`; signals validated per scenario |
| Biological deviation propagation | TESTED | IMPLEMENTED | - | IMPLEMENTED | - | repository `value_attr`; `RULES-005` fires for DB-persisted subjects |
| Docs | IMPLEMENTED | - | - | - | - | `docs/SYNTHETIC_DATA.md` |

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
| Alert center + detail + score breakdown | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | Alerts list (filterable) + detail with "why flagged" score decomposition |
| Triage (review/dismiss/escalate/request-analysis) | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | `PATCH /alerts/{id}/status` + TriagePanel (review/dismiss/false-positive/escalate) |
| False-positive handling | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | 5 tests | Strong single-signal stays <70, not CRITICAL |
| Convert to case | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | Alert→investigation with priority + note; audit `INVESTIGATION_CREATED`/`ALERT_CONVERTED` |

## Investigations (STAGE G)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Case creation + lifecycle | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | 4 API tests | OPEN/ESCALATED/CLOSED; convert from alert; list + create + workspace lifecycle; audit trail |
| Assignment | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | 8 hardening tests | Assign/unassign dialog `POST /investigations/{id}/assign` gated by `INVESTIGATIONS_ASSIGN`; audit; `assigned_to` list filter |
| Evidence management | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | 8 hardening tests | Sensitivity ACL, SHA-256 integrity (canonical `clean-sport-evidence-v1`), append-only version history, controlled soft delete; tab: add/edit/versions/integrity |
| Tasks | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | CRUD + close; `assigned_to_name` resolved on task rows |
| Notes (audited) | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | Audited investigator notes |
| Findings | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | 8 hardening tests | Investigator-controlled; FK evidence links with validity; cross-case links rejected |
| Timeline | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | Mixed events/reports/case work, `ALERT_SIGNAL` vs `CONTEXT` |
| Relationship graph | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | Custom SVG layout (no React Flow dependency) honoring the JSON contract; "association ≠ wrongdoing" |
| Investigation workspace page | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | 11 tabs: overview + intelligence + timeline + graph + evidence + … + report/ai/audit |

## AI (STAGE H)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Retrieval-grounded assistant | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | 4 API tests | Workspace AI tab; scoped to one case; claims typed (RECORDED_FACT/Analytical/INFERENCE/QUESTION), sources deterministic |
| Summaries / explanations / suggested questions | VERIFIED | IMPLEMENTED | IMPLEMENTED | - | API tests | Case summary, timeline summary, signal explanation, gaps, questions; global AI assistant page |
| Deterministic fallback | VERIFIED | IMPLEMENTED | IMPLEMENTED | - | API tests | No-LLM path; grounded fallback; never invents records/judgments |

## Reporting (STAGE I)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Report generation (structured sections) | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | API tests | Draft→FINAL→superseded versions; author/version/status per section; workspace Reports tab + publish |
| Report preview | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | - | - | Iterative preview in workspace (DRAFT/edit → publish); standalone print/export pending |
| Export (where feasible) | NOT_STARTED | - | - | - | - | |

## Landing Page & Authentication (update)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Cinematic landing intro (VERITY wordmark → zoom through I-dot → landing) | VERIFIED | - | IMPLEMENTED | - | Vitest + 2 Playwright | 1.76s CSS-transform path (measured dot, viewport-correct), ~240ms reduced-motion, once per session, skipped on hash/deep-link/back-forward, `pointer-events-none` + `aria-hidden` |
| Scroll reveals + focused nav (smooth scroll, hash, mobile close, emphasis) | VERIFIED | - | IMPLEMENTED | - | Vitest + Playwright | `Reveal` IntersectionObserver; `id="how-it-works"` navigation renamed; reduced-motion honored |
| Self-service account creation | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | +11 backend, Playwright | `POST /auth/register` → VIEWER; auto sign-in; 409 dup username/email; username regex |
| Password reset (request + redeem) | VERIFIED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | +12 backend, Playwright | `forgot-password` neutral/anti-enum + hashed single-use 30-min tokens (migration 0004); `reset-password` one-time redeem; dev-only `dev_reset_token` echo |
| Auth pages (Login/Signup/Forgot/Reset + AuthShell transitions) | VERIFIED | - | IMPLEMENTED | - | Vitest + Playwright | `?reset=1` banner; lazy routes `/signup`, `/forgot-password`, `/reset-password` |

## QA & Docs (STAGE J)

| Feature | Status | Backend | Frontend | Database | Tests | Notes |
|---|---|---|---|---|---|---|
| Unit tests (rules/ML/correlation/network/priority) | TESTED | - | - | - | 41 tests | features(11), rules(7), anomaly(5), correlation(8), network(5), priority(7) |
| API + authz tests | TESTED | - | - | - | 20 tests | auth(9), authz(11) |
| Integration tests (DB→repo→service→API) | TESTED | - | - | - | 7 tests | Full analysis run + traceability + unauth-block + investigations + AI/reporting flows |
| Investigation hardening tests (assignment/integrity/links/guard) | VERIFIED | - | - | - | 8 tests | `test_investigation_hardening.py`; full suite 144 passed (post auth-update) |
| End-to-end workflow test | TESTED | - | - | - | 5 tests | Scenario validation (network/multi-source/false-positive); alert→case→report flow |
| Analytical validation (scenario separation) | TESTED | - | - | - | 5 tests | network>normal, multi>normal, FP<70; graph features excluded from anomaly model |
| Frontend unit/component tests (Vitest + RTL) | TESTED | - | - | - | 43 tests | utils, nav, auth store, api client, TriagePanel, Landing (intro/reveal/ids) |
| Frontend E2E critical journey (Playwright) | VERIFIED | - | - | - | 2 specs | landing intro (3 variants) + journey + signup→forgot→reset→login (5 pass) |
| Frontend typecheck / lint / build | VERIFIED | - | - | - | - | `tsc -b` clean; ESLint 0 errors; `vite build` 1677 modules |
| `docs/API.md` | NOT_STARTED | - | - | - | - | |
| `docs/DATA_DICTIONARY.md` | NOT_STARTED | - | - | - | - | |
| `docs/DOMAIN_VALIDATION.md` | VERIFIED | - | - | - | - | 20 concepts validated vs WADA/ISTI/ISII/ITA; D-010..D-012 raised |
| Dashboard metrics from backend | VERIFIED | IMPLEMENTED | IMPLEMENTED | - | - | `GET /dashboard` aggregates; cards + quick links |
| Error/empty/loading states everywhere | VERIFIED | IMPLEMENTED | IMPLEMENTED | - | - | `states.tsx` (PageLoading/Spinner/Skeleton/SkeletonRows) + ErrorBoundary + toast feedback |
| Demo workflow (directive §66) verified | VERIFIED | IMPLEMENTED | IMPLEMENTED | - | - | Manual end-to-end on seeded data + automated E2E journey |

---

*Updated at the end of each stage. A feature is not complete merely because code exists.*
