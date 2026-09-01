# Traceability Matrix

**Living document.** Requirements map to implementation modules, files, APIs, database
entities and tests. Updated continuously during implementation.

Traceability format (per directive §48):

```text
Requirement → Module → File → API → Database entity → Test
```

Requirement identifiers reference the master directive sections (§N) and the research
documents (PRD `01_DETAILED_PRD.md` FR-*, user stories US-*; `04_ALGORITHMS.md`;
`07_TESTING_AND_DATA.md` scenarios).

---

## A. Identity & Access

| ID | Requirement | Module | File | API | DB | Test |
|---|---|---|---|---|---|---|
| §35 / FR-AUTH-001..004 / US-001,002 | Authentication, password hashing, tokens, logout, current-user, protected routes | `app/security/` | `app/security/auth.py`, `app/api/routes/auth.py` | POST `/api/v1/auth/login`, POST `/api/v1/auth/logout`, GET `/api/v1/auth/me` | `users`, `roles`, `role_permissions` | `test_auth.py` |
| §36 / FR-AUTH-004 | RBAC roles: ADMINISTRATOR, INVESTIGATOR, INTELLIGENCE_ANALYST, VIEWER; backend enforcement | `app/security/` | `app/security/rbac.py`, `app/api/deps.py` | middleware on all protected routes | `roles`, `permissions`, `role_permissions`, `users.role_id` | `test_authz.py` |
| §37 / FR-CASE-007 | Audit log of sensitive actions | `app/audit/` | `app/audit/service.py`, `app/api/routes/audit.py` | GET `/api/v1/audit` | `audit_events` | `test_audit.py` |

---

## B. Intelligence

| ID | Requirement | Module | File | API | DB | Test |
|---|---|---|---|---|---|---|
| §41 / FR-INTEL-001..005 / US-010..012 | Intelligence inbox, ingestion, source provenance, entity linking, dedupe by source ID/hash | `app/intelligence/` | `app/intelligence/service.py`, `app/intelligence/ingestion.py`, `app/api/routes/intelligence.py` | POST `/api/v1/intelligence/import`, POST/GET `/api/v1/intelligence`, GET `/api/v1/intelligence/{id}`, POST `/api/v1/intelligence/{id}/assess` | `intelligence_sources`, `intelligence_reports`, `source_assessments`, `intelligence_tags`, `intelligence_relationships` | `test_intelligence.py` |
| §16 / scenario 8 | Entity resolution (deterministic + fuzzy), resolution basis recorded, never auto-merge uncertain | `app/intelligence/` | `app/intelligence/entity_resolution.py` | invoked during import/assess | `intelligence_reports.subject_*`, resolution records | `test_entity_resolution.py` |
| §14 | Synthetic ingestion (CSV/JSON/manual/seed) | `app/intelligence/` | `app/intelligence/ingestion.py` | POST `/api/v1/intelligence/import` | `intelligence_reports` | `test_ingestion.py` |

---

## C. Analytics

| ID | Requirement | Module | File | API | DB | Test |
|---|---|---|---|---|---|---|
| §17 / §57 / FR-ANALYSIS-001..003 / `04` §3 | Deterministic rule engine; versioned rules; structured results | `app/analysis/rules/` | `app/analysis/rules/engine.py`, `app/analysis/rules/definitions/` | POST `/api/v1/analysis/run`, GET `/api/v1/analysis/runs/{id}`, GET `.../results` | `rule_versions`, `rule_results`, `indicators`, `analysis_runs` | `test_rule_engine.py` |
| §18 / `04` §2 | Feature engineering; reproducible; named/typed/versioned features | `app/analysis/features/` | `app/analysis/features/engine.py` | served via analysis run + feature snapshots | `feature_snapshots`, `model_versions` | `test_feature_engineering.py` |
| §19 / §20 / `04` §4-5 | Isolation Forest anomaly; normalized score; feature-level explanation; no guilt claim | `app/analysis/anomaly/` | `app/analysis/anomaly/model.py`, `app/analysis/anomaly/explain.py` | analysis run pipeline | `model_versions`, `anomaly_results`, `feature_snapshots` | `test_anomaly.py` |
| §21 / `04` §6 | Temporal rolling-window correlation (default 45d) | `app/analysis/correlation/` | `app/analysis/correlation/temporal.py` | analysis run pipeline | `correlation_results`, `indicators` | `test_temporal_correlation.py` |
| §22 / `04` §7 | Cross-source correlation; source diversity ≠ proof | `app/analysis/correlation/` | `app/analysis/correlation/cross_source.py` | analysis run pipeline | `correlation_results` | `test_cross_source.py` |
| §23 / `04` §8 | Network analysis; degree, weighted degree, connected alerts, relationship diversity; association ≠ wrongdoing | `app/analysis/network/` | `app/analysis/network/scoring.py`, `app/analysis/network/graph.py` | GET `/api/v1/athletes/{id}/relationships`, `/investigations/{id}/graph` | `entity_relationships`, `relationship_types`, `network_results` | `test_network.py` |
| §24 / `04` §10-11 | Composite priority score `P=0.25R+0.20A+0.20C+0.15T+0.10N+0.10S`; 0-100; LOW..CRITICAL; decomposition | `app/analysis/scoring/` | `app/analysis/scoring/priority.py` | analysis run pipeline | `priority_scores`, `alerts` | `test_priority.py`, `test_priority_scoring.py` |
| §58 / FR-ANALYSIS-002 | Reproducibility: params, seed, feature/rule versions, timestamps | `app/analysis/` | `app/analysis/runs.py` | GET `/api/v1/analysis/runs/{id}` | `analysis_runs` | `test_runs.py` |

---

## D. Alerts

| ID | Requirement | Module | File | API | DB | Test |
|---|---|---|---|---|---|---|
| §25 / FR-ALERT-001..002 | Alert generation on thresholds, correlations, high-severity rules, network clusters | `app/alerts/` | `app/alerts/service.py` | generated by analysis pipeline | `alerts`, `alert_signals` | `test_alerts.py` |
| §26 | Human triage: inspect, review, dismiss, escalate, request analysis, convert | `app/alerts/` | `app/api/routes/alerts.py` | POST `/api/v1/alerts/{id}/review`, `/convert-to-case` | `alerts`, `alert_reviews`, `investigations` | `test_alert_triage.py` |
| §7 / §12 (scenario 7) | False-positive handling and feedback | `app/alerts/` | `app/alerts/service.py` | POST `/api/v1/alerts/{id}/review` (status FALSE_POSITIVE) | `alert_reviews`, `case_outcomes` | `test_false_positive.py` |

---

## E. Investigations

| ID | Requirement | Module | File | API | DB | Test |
|---|---|---|---|---|---|---|
| §27 / FR-CASE-001..007 | Investigation case management; lifecycle states | `app/investigations/` | `app/investigations/service.py`, `app/api/routes/investigations.py` | POST/GET `/api/v1/investigations`, GET/PATCH `/api/v1/investigations/{id}`, POST `/assign` | `investigations`, `investigation_assignments` | `test_investigations.py` |
| §29 / case evidence | Evidence as first-class entity; links; metadata; hash where implemented (no fabricated crypto) | `app/evidence/` | `app/evidence/service.py` | POST `/api/v1/investigations/{id}/evidence` | `evidence_items`, `evidence_links`, `evidence_metadata` | `test_evidence.py` |
| §30 | Investigation tasks (TODO/IN_PROGRESS/BLOCKED/COMPLETED) | `app/investigations/` | `app/investigations/tasks.py` | POST `/api/v1/investigations/{id}/tasks` | `investigation_tasks` | `test_tasks.py` |
| §31 | Investigation notes (author, timestamp, classification, audited/immutable) | `app/investigations/` | `app/investigations/notes.py` | POST `/api/v1/investigations/{id}/notes` | `investigation_notes` | `test_notes.py` |
| §28 / §32 / §66 | Investigation workspace: timeline, graph, evidence, intelligence, findings, audit | `app/investigations/` | `app/api/routes/investigations.py` | GET `/api/v1/investigations/{id}/timeline`, `/graph` | `investigation_findings`, `investigation_actions`, relationships | `test_investigation_workspace.py` |
| FR-CASE-006 / §27 | Case outcomes (allowed: closed no-action, false positive, unsubstantiated, escalated, referred, monitoring) | `app/investigations/` | `app/investigations/outcomes.py` | PATCH `/api/v1/investigations/{id}` | `case_outcomes` | `test_outcomes.py` |

---

## F. Reporting

| ID | Requirement | Module | File | API | DB | Test |
|---|---|---|---|---|---|---|
| §34 / FR-REPORT-001 | Structured investigation report; preview; no automatic guilt conclusion | `app/reports/` | `app/reports/service.py`, `app/api/routes/reports.py` | POST/GET `/api/v1/investigations/{id}/report` | `investigation_reports`, `report_versions` | `test_reports.py` |

---

## G. AI Assistant

| ID | Requirement | Module | File | API | DB | Test |
|---|---|---|---|---|---|---|
| §33 / §20 / US-040,041 | Retrieval-grounded AI; summarize/explain/suggest questions; deterministic fallback; grounded output; no fabrications | `app/ai/` | `app/ai/service.py`, `app/ai/prompts.py`, `app/ai/fallback.py` | POST `/api/v1/assistant/...` (scoped to a case) | read-only over case data | `test_ai.py` |

---

## H. Frontend / UX

| ID | Requirement | Module | File | API | Test |
|---|---|---|---|---|---|
| §38 / §39 | Navigation + Dashboard with real backend-derived metrics | `features/dashboard` | `frontend/src/pages/DashboardPage.tsx`, `.../api` | GET `/api/v1/dashboard/summary` | `dashboard` e2e |
| §40 | Athlete intelligence profile (tabs) | `features/athletes` | `frontend/src/pages/AthleteProfilePage.tsx` | GET `/api/v1/athletes/{id}`, `/timeline`, `/relationships`, `/alerts` | e2e |
| §41 | Intelligence inbox with filters/sort | `features/intelligence` | `frontend/src/pages/IntelligenceInboxPage.tsx` | GET `/api/v1/intelligence` | e2e |
| §42 | Alert center + score decomposition | `features/alerts` | `frontend/src/pages/AlertCenterPage.tsx`, `AlertDetailPage.tsx` | GET `/api/v1/alerts`, GET `/api/v1/alerts/{id}` | e2e |
| §28 | Investigation workspace (center stage) | `features/investigations` | `frontend/src/pages/InvestigationWorkspacePage.tsx` | investigation endpoints | e2e + `test_investigation_workspace` |
| §32 / §8 | Relationship graph (React Flow, real data) | `components/graph` | `frontend/src/components/graph/RelationshipGraph.tsx` | `/relationships`, `/graph` | e2e |
| §43-45 | Visual design, accessibility, error/loading/empty states | `components/ui`, `layouts` | shadcn primitives + skeleton/empty/error components | n/a | manual + e2e |

---

## I. Data / Infrastructure

| ID | Requirement | Module | File | DB | Test |
|---|---|---|---|---|---|
| §14, §15 | Deterministic synthetic data generator + 9 scenarios; seed-data / reset-data | `scripts/`, `app/data/` | `scripts/seed.py`, `scripts/reset.py`, `app/data/generator.py` | all entities | `test_generator.py`, analytical tests |
| §11, §9 | Repository structure; PostgreSQL; Alembic | `backend/`, `migrations/` | `alembic/versions/*` | all | migration apply/rollback |
| §10 | Docker Compose (frontend/backend/postgres); `.env.example`; no secrets | root | `docker-compose.yml`, `.env.example`, `backend/Dockerfile`, `frontend/Dockerfile` | n/a | compose up smoke test |
| §12 | Traceability doc | `docs/` | `docs/TRACEABILITY.md` | n/a | n/a |
| §49 | Implementation status doc | `docs/` | `docs/IMPLEMENTATION_STATUS.md` | n/a | n/a |
| §51 | API doc | `docs/` | `docs/API.md` | n/a | n/a |
| §52 | Data dictionary | `docs/` | `docs/DATA_DICTIONARY.md` | n/a | n/a |
| §50 | Decision log | `docs/` | `docs/DECISIONS.md` | n/a | n/a |
| Domain | Domain validation (20 intelligence/investigation concepts → authoritative sources → software mapping → modification flags) | `docs/` | `docs/DOMAIN_VALIDATION.md` | n/a | n/a |

---

*This matrix is expanded and kept current during each stage of implementation.*
