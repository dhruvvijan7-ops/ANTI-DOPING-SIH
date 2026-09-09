# Repository Re-Verification, Gap Analysis & Continuation Report

**Project:** SIH1721 Anti-Doping Intelligence & Investigations Platform (CleanSport)
**Date:** 2026-09-07
**Source of truth:** actual repository + executable code + database + runtime behavior (HANDOVER used only for intended-state comparison)
**Method:** inspect → verify → classify → report. No code was changed during this audit.

---

## 1. Executive Summary

The repository contains a **functional, tested backend** for the anti-doping
intelligence pipeline (authentication/RBAC, analytics engine with rules + Isolation
Forest + temporal/cross-source/network analysis + explainable versioned scoring,
alert triage → investigation workflow, evidence/tasks/notes/findings, grounded AI
decision support, versioned reporting, audit trail). The backend was proven this
session: **84/84 tests pass** and a **live 78/78 HTTP verification** on a fresh dev
database is on record (see `docs/FINAL_VERIFICATION.md`).

The project is nevertheless **not yet an end-to-end product**: there is **no frontend
whatsoever** (`frontend/`, `ml/`, `data/`, `scripts/` do not exist), **no in-application
synthetic-data generator/registry** (STAGE C not implemented; `synthetic_scenarios` is
empty and `run_seed` creates identity rows only), and **no dashboards/athlete/intelligence/
testing/travel read APIs** despite those tables existing. `docker compose up --build`
cannot complete because the `frontend` build context is missing. Consequently the
intended demo journey (§84 checklist) is achievable **end-to-end only at the API level**.

Overall maturity: **backend core = TESTED; product/demo = PARTIALLY FUNCTIONAL;
full-stack = NOT IMPLEMENTED.**

---

## 2. Repository Reality

Actual layout (verified by filesystem inspection, not docs):

```
/                         README.md, LICENSE, CONTRIBUTING.md, CHANGELOG.md,
                          .gitignore, .env.example, docker-compose.yml
backend/
  app/
    api/routes/           auth, users, health, analysis, alerts, investigations,
                          ai, reports
    ai/                   retrieval.py, service.py (fallback + LLM wrapper)
    analysis/             features, rules, anomaly, correlation, network, priority,
                          runner, repository, serializers, contracts, cli
    core/                 config, exceptions, logging
    db/                   session, seed (identity only)
    investigations/       serializers
    models/               identity, subjects, intelligence, events, relationships,
                          analytics, scenarios, investigations, reports, audit
    schemas/
  migrations/versions/    0001_identity_security, 93e0ebdb044c_domain_and_analytics,
                          0002_investigations_reports
  tests/                  14 test modules
docs/                     handover.md (UNTRACKED in git), FINAL_VERIFICATION.md
                          (UNTRACKED), ARCHITECTURE, DATABASE, DECISIONS,
                          DOMAIN_VALIDATION, IMPLEMENTATION_BASELINE,
                          IMPLEMENTATION_STATUS, PROJECT_STATUS, TESTING, TRACEABILITY
.github/workflows/ci.yml  backend pytest only
```

What does NOT exist: `frontend/`, `package.json`, any Node tooling; `ml/`; `data/`;
`scripts/`; CI steps beyond backend pytest.

Git reality: branch `main`, HEAD `c13d7f7` (pushed, `origin` = the expected GitHub repo);
working tree contains uncommitted security fixes (config production-guard, deps 401,
docs disabling), doc corrections, and untracked `docs/handover.md` +
`docs/FINAL_VERIFICATION.md`.

Environment finding: **Docker engine was down at audit start** (caused transient
"all tests error" — DB on host port 54320 unreachable). After restarting Docker
Desktop, postgres recovered and the full suite passed; the DB-dependent suite requires
the `cleansport-postgres` container.

---

## 3. Feature Status Matrix

Statuses follow the directive taxonomy. "Evidence" cites tests or live probes run this session/concurrent session.

| Area | Requirement | Status | Evidence | Gaps | Priority |
|---|---|---|---|---|---|
| Auth | login / logout / me, JWT + bcrypt | TESTED | test_auth.py 13 tests; live 401s inc. expired/garbage | stateless logout (D-009), no rate-limit | P1 |
| RBAC | ADMIN/INVESTIGATOR/ANALYST/VIEWER, server-side | TESTED | test_authz.py 11 tests; live matrix | `INVESTIGATIONS_ASSIGN` unused | P0 |
| Domain DB | subjects/intel/events/relationships/analytics/alerts/investigations/reports/audit | TESTED | migrations+constraint probes; 44 tables at head | see §8 | P0 |
| Domain read APIs | athletes/entities/intelligence/testing/ABP/travel/whereabouts listings | NOT IMPLEMENTED | no `/athletes`, `/intelligence`, `/dashboard` routes | dashboard+profile story missing | P0 |
| Analysis engine | full pipeline run + persistence | TESTED | test_analysis_api.py; live run stages/counts | subject filter partial; no async | P1 |
| Rules | 9 deterministic versioned rules | TESTED | test_rule_engine.py 8 tests | none | – |
| Isolation Forest | sklearn IF, normalized score, explanation | TESTED | test_anomaly.py 5 tests; live | version fixed 1.0 | P2 |
| Temporal | 45-day burst correlation | TESTED | test_correlation.py | — | – |
| Cross-source | 90-day correlation + dedupe | TESTED | test_correlation.py | — | – |
| Network | relevance scoring, graph | TESTED | test_network.py 5 tests | graph features excluded from IF (done) | – |
| Priority scoring | 0.25/0.20/0.20/0.15/0.10/0.10, 5 classes, explainable | TESTED | test_priority.py 7 tests; live | prototype thresholds (documented) | – |
| Alerts | generate/persist/list/detail | TESTED | test_analysis_api.py; live chain | — | – |
| Alert workflow | review/dismiss/escalate/false-positive/monitor/convert/status | TESTED | test_investigations_api.py; live | — | – |
| Investigations | create(convert/direct), detail, close, overview, intel, timeline, relationships | TESTED | test_investigations_api.py; live | — | – |
| Assignment | case/task assignment | PARTIALLY FUNCTIONAL | live convert+task assign | no re-assign endpoint; permission dead | P1 |
| Evidence | add/list/edit | PARTIALLY FUNCTIONAL | test/live evidence add+patch | no sensitivity/integrity/version-history | P1 |
| Notes | authored, audited | TESTED | live note + audit | — | – |
| Tasks | CRUD + close, assignee/due | TESTED | live task lifecycle | — | – |
| Findings | investigator-authored, distinct from signals | PARTIALLY FUNCTIONAL | live findings | evidence link is free-text, no FK | P1 |
| Timeline | derived mixed event view | TESTED | live timeline | no filter API params beyond case | P2 |
| Relationship graph | JSON contract for React Flow | TESTED (backend) | live graph 4 nodes/3 edges | frontend NOT IMPLEMENTED | P1 |
| AI assistant | summary/timeline/signal/gaps/questions/report-draft | TESTED | test_ai_reporting.py 4 tests; live 6 ops | provider-dependent only when configured | – |
| AI grounding/safety | no fabrication, NOT_DETERMINED, claim types, prompt hygiene | TESTED | live pre/post-evidence checks; service.py SAFETY_POLICY | no evidence-view tampering guard | P1 |
| Reports | structured, versioned, publish/edit/supersede | TESTED | test_ai_reporting.py; live {2:DRAFT,1:SUPERSEDED} | no preview/export | P2 |
| Audit | action trail with actor/action/target/timestamp/metadata | TESTED | live audit entries; audit RBAC 403 analyst | no retention policy | P2 |
| Confidential reporting | whistleblower/informant flow | NOT IMPLEMENTED | no endpoint/model | STAGE C/whistleblower scope | P2 |
| Synthetic data | generator, registry, 6+ scenarios, seeds | NOT IMPLEMENTED | `synthetic_scenarios`=0 rows; `run_seed` identity-only | STAGE C entirely absent | P0 |
| Frontend | any UI | NOT IMPLEMENTED | no directory | full demo impossible | P0 |
| Docker | compose full stack | PARTIALLY FUNCTIONAL | postgres+backend run; `frontend` build fails | missing context | P0 |
| CI | backend pytest | EXISTS (not run in-session) | ci.yml | no lint/type tests, GitHub-hosted only | P2 |
| Docs | match reality | PARTIAL | CHANGELOG/status corrected this session; README has mojibake | several status tables stale | P2 |

---

## 4. End-to-End Workflow Status

Handover §14.1 pipeline, whether each link exists/disconnected/produces+persists data/API-exposed/frontend-exposed/tested:

| Stage | Exists | Connected | Real data | Persisted | API | Frontend | Tested |
|---|---|---|---|---|---|---|---|
| Data (sources) | PARTIAL | — | yes (manual/test/verify script seeds) | yes | NO | NO | PARTIAL |
| Normalization | PARTIAL (in-feature) | yes | yes | feature snapshots | via run | NO | yes |
| Entity Resolution | NO (dedupe only, per-key) | — | — | no | no | NO | partial |
| Intelligence Analysis | yes | yes | yes | stage tables | yes | NO | yes |
| Signals | yes | yes | yes | result tables | yes | NO | yes |
| Correlation | yes | yes | yes | correlation_results | yes | NO | yes |
| Explainable Priority Score | yes | yes | yes | priority_scores | yes | NO | yes |
| Alert | yes | yes | yes | alerts/alert_signals | yes | NO | yes |
| Human Review | yes | yes | yes | alerts + audit | yes | NO | yes |
| Investigation | yes | yes | yes | investigations | yes | NO | yes |
| Evidence/Notes/Tasks/Findings | yes | yes | yes | tables | yes | NO | yes |
| AI-Assisted Synthesis | yes | yes | yes | response only (not stored) | yes | NO | yes |
| Report | yes | yes | yes | reports + report_versions | yes | NO | yes |
| Audit Trail | yes | yes | yes | audit_events | yes | NO | yes |

**Broken/missing links:** every link that requires the UI is missing; "Data" has no
in-app generator; "intelligence inbox / athlete profile / dashboard" stages do not exist
as API features.

---

## 5. Intelligence Engine Status

| Subsystem | Status | Notes |
|---|---|---|
| Rules | TESTED | 9 versioned rules (RULES-001..009); rule_results persisted per run; rule version 1. |
| ML (Isolation Forest) | TESTED | sklearn 1.7.2; real execution; anomaly_results with normalized score + contributions; model version 1.0; deterministic/reproducible (n_estimators=200, contamination=0.05). |
| Temporal analysis | TESTED | 45-day window; burst detection; real event dates from DB. |
| Cross-source correlation | TESTED | 90-day window; supports multi source-type corroboration; dedup by key. |
| Network analysis | TESTED | degree/diversity/connected-priority scoring; graph JSON; relationship is context, not proof (label + disclaimer). |
| Priority scoring | TESTED | weights 0.25/0.20/0.20/0.15/0.10/0.10; components normalized 0–100; classes 0–29 LOW … 85–100 CRITICAL; composite persisted with decomposition + explanation. |
| Explainability | TESTED | traceable chain alert → priority → components → signals → records (live-verified). |
| Persistence/versioning | TESTED | feature_version 2, model 1.0, rule 1, per-run; historical runs immutable. |

Scenario-specific verification: NORMAL stays low, NETWORK > NORMAL, MULTI_SOURCE >
NORMAL, FALSE_POSITIVE stays reviewable (all pipeline tests pass); TEMPORAL and
isolated-anomaly validated at unit level only; no scenario registry.

---

## 6. Frontend Status

**NOT IMPLEMENTED.** No `frontend/` directory, no `package.json`, no source. None of
§35–§39, Vitest/RTL/Playwright, routing, API integration, loading/empty/error/populated
states, or React Flow exists. `docker compose build frontend` fails:

```
unable to prepare context: path "...\frontend" not found
```

---

## 7. Backend/API Status

Endpoints verified present (62 route decorators across 8 routers), all RBAC-guarded:

- `/health`, `/` (root)
- `/auth`: POST login, POST logout, GET me
- `/users`: GET/POST, roles GET/POST/PATCH, permissions GET
- `/analysis/runs` POST (pipeline trigger), GET list, GET detail, per-stage
  (features/rules/anomalies/correlations/network/priority), subject results/features
- `/alerts`: GET list, GET detail, PATCH status, POST review/dismiss/false-positive/
  escalate/convert
- `/investigations`: GET/POST, PATCH, POST close, GET detail/intelligence/timeline,
  evidence GET/POST/PATCH, tasks GET/POST/PATCH, notes GET/POST/PATCH, findings
  GET/POST/PATCH, relationships GET, audit GET
- `/investigations/{id}/reports`: GET/POST, PATCH, POST publish
- `/investigations/{id}/ai`: summary, timeline-summary, signal-explanation,
  information-gaps, questions, report-draft

Missing vs §40: `/dashboard`, `/athletes`, `/intelligence`, top-level `/evidence`,
top-level `/relationships` (data exists in DB but has no read API). No pagination on
most lists. No request/response OpenAPI for these missing domains either.

---

## 8. Database Status

At migration head (`0002_investigations_reports`): **44 tables** (43 domain +
alembic_version) in the verification DB. Confirmed: FK enforcement, 5 named Admiralty
CHECK constraints, 0 orphan FKs, story-level indexes, alert→signals traceability
(55 signals / 5 runs).

Important finding: **the checked-out dev database `clean_sport` is NOT at head** —
alembic_version `93e0ebdb044c`, so investigations/reports tables are absent there until
`alembic upgrade head` runs (docker backend does this on boot).

Design deviations from §41 (legitimate, documented): no `tenants`, `signals`,
`signal_evidence`, `evidence_links`, `timeline_events`, `investigation_members` tables;
instead analytics result tables + alert_signals + derived timeline + direct
investigation FKs are used. Identified debt: no CHECK on investigations priority/status
and report status; 12 unindexed FK columns (alerts.analysis_run_id,
alerts.priority_score_id confirmed missing via probe).

---

## 9. Authentication / RBAC / Security Status

**Verified:** JWT (HS256) + bcrypt; server-side RBAC from DB; role/permission model
(4 roles, 26 permission keys); audit middleware on protected writes; `.env` gitignored;
`.env.example` placeholder-only. Live-verified: valid/invalid/unknown/malformed/expired/
non-UUID tokens; full RBAC matrix incl. analyst→403 on audit.

**Fixed during audit (uncommitted, will ship with next commit):** production fail-early
on default/short JWT secret and default admin password; `/docs`/`/redoc`/openapi disabled
in production; malformed-token 500 → 401 (4 new tests).

**Verified-but-risk:** logout is a client-side no-op (token remains valid); no login
rate limiting; `INVESTIGATIONS_ASSIGN` permission never enforced; evidence access
controls exist at case level but no per-evidence ACL; no upload path exists yet
(no upload security to verify — nothing to upload to).

---

## 10. AI Status

**Real, grounded, decision-support only — default path requires no external provider.**
`DeterministicFallbackAIService` (default) is a fully-grounded structured summarizer of
retrieved DB records; it returns `NOT_DETERMINED` (exact phrase) when data absent, never
invents evidence/witnesses/events/sources/citations, classifies claims
(RECORDED_FACT/ANALYTICAL_SIGNAL/INFERENCE/INVESTIGATIVE_QUESTION), refuses guilt/
sanction determinations, scopes retrieval to one case, and treats untrusted content as
data (SAFETY_POLICY + prompt-injection note). `OpenAICompatibleLLMService` is optional,
provider-agnostic (stdlib), only instantiated when credentials are configured, and
primes its prompt with the deterministic result. Live-verified pre/post evidence and
case-scoping behavior. **Not** provider-mocked — but the LLM path is NOT exercised in
tests (no credentials); correctness of the fallback path is what is tested.

---

## 11. Reporting Status

**Real and versioned (backend).** Draft → publish (FINAL) → edit → prior version
SUPERSEDED; per-version author/status/dates; history verified live (`{2:DRAFT,
1:SUPERSEDED}`). Generated from real case data (originating alert, signals, evidence,
findings, timeline, relationships, audit count) by the AI report-draft operation.
Missing: preview/export, and per §29 full structural fidelity ("Purpose/Scope",
"Background", "Trigger/Initial Intelligence", "Assessment", "Recommendations" are
sections an investigator cannot yet author/edit through the API — only via AI draft +
publish).

---

## 12. Synthetic Data Status

- Schemas: `synthetic_scenarios` table exists (migration 93e0ebdb044c) — **empty (0 rows)**.
- In-app seeding: `run_seed` seeds **identity only** (4 roles, 4 users, 26 permissions).
  The domain dataset (athletes, sources, events, reports, relationships) exists only via
  test helpers (`tests/support_domain.py`) and the verification harness — **not** part of
  the product.
- No generator, no fixed seeds, no scenario IDs, no repeatable `seed-data`/`reset-data`
  CLI, no ground-truth labels. §24/§25/§12 of the directive are unmet (STAGE C not started).
- Covered scenario archetypes (test-side only): NORMAL, NETWORK, MULTI_SOURCE,
  FALSE_POSITIVE (pipeline level); TEMPORAL/isolated-anomaly (unit level). No registry.

---

## 13. Testing Status

Executed this session: **`pytest -q` → 84 passed, EXIT=0** (auth 13, authz 11, features
11, correlation 8, rules 8, anomaly 5, network 5, scenarios 5, priority 7,
investigations 4, ai_reporting 4, analysis_api 3). Test DB = dedicated `clean_sport_test`
schema, migrated base→head, seeded, truncated per test, dropped after session.

Also on record this session: live HTTP verification **78/78 PASS** against a fresh
database; DB constraint probes PASS; `compileall` PASS.

**test exists ≠ meaningful** caveats: the LLM provider path is untested (no live
provider); no alert-re-open/reassign tests; no evidence-versioning test; no missing-athlete
domain test; no intelligence-report read-API tests (API absent); no frontend/e2e tests
(no frontend). Skips: none. Starlette/TestClient deprecation + PytestCollectionWarning
(non-fatal).

---

## 14. Documentation / Repository Status

- README: correct intent, but **mojibake** (`�?"` artifacts) and describes nothing of
  STAGE D/E/F/G/H/I content; lists `frontend/` in repository layout that does not exist.
- `.gitignore`: good (env, keys, caches, ML artifacts). `.env.example`: placeholders only — good.
- CHANGELOG/IMPLEMENTATION_STATUS: corrected this session (false CHECK-constraint claim
  removed; compose + assignment rows updated); other rows remain stale vs actuals.
- docs present: ARCHITECTURE, DATABASE, DECISIONS, DOMAIN_VALIDATION, TESTING,
  PROJECT_STATUS, IMPLEMENTATION_BASELINE, IMPLEMENTATION_STATUS, TRACEABILITY,
  FINAL_VERIFICATION. `docs/API.md` and `docs/DATA_DICTIONARY.md` promised but absent.
- **`docs/handover.md` is untracked in git.**
- CI: backend pytest on push/PR only (postgres service); no lint/type/frontend; not
  executed in-session (GitHub-hosted).

---

## 15. Critical Gaps (blockers to definition of done)

| # | Gap | Blocks | Severity |
|---|---|---|---|
| G1 | No frontend (any) | §84 demo, §65 DoD items 2–27, E2E | **P0** |
| G2 | No synthetic-data generator/registry/CLI/scenarios (STAGE C) | §24/25/12, reproducible demo, ground truth | **P0** |
| G3 | No domain read APIs (dashboard/athletes/intelligence/testing/ABP/travel/whereabouts) | DoD items 3–9 | **P0** |
| G4 | No re-assignment endpoint; dead INVESTIGATIONS_ASSIGN | DoD item 16 | **P1** |
| G5 | Security hardening (rate limit, real logout/denylist, evidence ACL, upload hygiene) | §44; D-009 tradeoff | **P1** |
| G6 | Evidence/history integrity (sensitivity, hashes, versioning) & finding→evidence link | §19, §20 | **P1** |
| G7 | 12 unindexed FK columns; CHECKs on investigation/report status | scale/audit | **P2** |
| G8 | Reporting section authoring + preview/export | §29 | **P2** |
| G9 | Docs drift (README mojibake, docs/API.md, DATA_DICTIONARY.md, untracked handover) | §89 | **P2** |

---

## 16. Recommended Implementation Order

1. **Correctness/end-to-end dependencies first:** G3 + G2 (seed/generator + domain read
   APIs: `/dashboard`, `/athletes`, `/intelligence`, `/events`, `/relationships`) — backend,
   with tests, keeping current pipelines intact (Rule 3).
2. **Core intelligence:** (already built/tested) — add temporal/isolated-anomaly
   pipeline-scenario tests + scenario registry population so §24 scenarios are runtime-data.
3. **Investigation workflow:** G4 re-assignment + enforce permission; G6 evidence
   integrity + finding→evidence FK.
4. **Security:** G5 (login rate-limit, revocable tokens or documented acceptance,
   evidence ACL at case level).
5. **Testing:** broaden domain-API tests (missing-athlete, intel validation, pagination),
   wire CI to run against docker postgres locally too.
6. **UX:** G1 frontend (React/Vite/Tailwind per §30) consuming existing contracts — the
   largest single block; do after APIs stabilize (Rule 9 contract sync).
7. **Documentation:** G9 (README rewrite with correct encoding, API/data docs, track
   handover).
8. **Polish:** charts/filters/graph interactions; report preview/export.

Follow: Foundation → Domain → Data → Intelligence → Scoring → Alerts → Investigations →
Evidence → AI → Reports → Audit → Hardening (adapted: intelligence chain done; resume at
Data + Domain-read APIs, then frontend).

---

## 17. Definition of Done (per §65 checklist)

| Item | State |
|---|---|
| 1 Log in | COMPLETE |
| 2 Dashboard | MISSING |
| 3 Synthetic intelligence visible | PARTIAL (open ended; data only via API/tests) |
| 4 Athlete/entity profile | MISSING (no read API) |
| 5 Review history | PARTIAL |
| 6 Testing/ABP review | MISSING (modeled only) |
| 7 Intelligence review | MISSING (modeled only) |
| 8 Travel/whereabouts review | MISSING (modeled only) |
| 9 Relationships review | PARTIAL (investigation-graph only) |
| 10 Automated signal | COMPLETE |
| 11 Priority score | COMPLETE |
| 12 "Why flagged" | COMPLETE |
| 13 Open alert | COMPLETE (API) |
| 14 Decide | COMPLETE |
| 15 Create investigation | COMPLETE |
| 16 Assign investigators | PARTIAL (no re-assign; permission unused) |
| 17 Add evidence | COMPLETE (basic) — PARTIAL for integrity/versioning |
| 18 Add notes | COMPLETE |
| 19 Create tasks | COMPLETE |
| 20 Timeline | COMPLETE (API) |
| 21 Relationships | COMPLETE (API) |
| 22 Findings | PARTIAL (evidence link not FK) |
| 23 AI grounded summary | COMPLETE (fallback) |
| 24 Generate report | COMPLETE |
| 25 Review report | COMPLETE (API) |
| 26 Close/continue | COMPLETE |
| 27 Audit trail | COMPLETE |
| §65 overall (UI-journey) | **UNVERIFIED / MISSING — no frontend** |
| Frontend build | MISSING |
| Backend runs | COMPLETE (verified) |
| Migrations work | COMPLETE |
| Tests pass | COMPLETE (84/84) |
| Docker full stack | PARTIAL (frontend broken) |
| CI | UNVERIFIED (exists, not run) |
| Docs match reality | PARTIAL |

---

## Phase 15 — HALT

Implementation has **not** been started. The working tree contains only the pre-existing
uncommitted security/doc fixes; this audit changed no application code. The report above
is the authoritative input for the next implementation phase.