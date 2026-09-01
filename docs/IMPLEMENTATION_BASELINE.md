# Implementation Baseline

**Date:** 2026-09-01
**Status:** Baseline analysis — no implementation code exists yet

This document captures the state of the repository *before* implementation and maps the
specification requirements to the planned codebase. It serves as the starting reference
for `TRACEABILITY.md`, `DECISIONS.md` and `IMPLEMENTATION_STATUS.md`.

---

## 1. Existing Architecture

The repository is **empty of application code**. The directory contains only the
specification package:

```
C:\Users\dhruv\OneDrive\Desktop\College\ANTI DOPING\
├── RESEARCH FOR ANTI DOPING\
│   ├── README.md
│   ├── 00_MASTER_SPECIFICATION.md
│   ├── 01_DETAILED_PRD.md
│   ├── 02_DETAILED_ARCHITECTURE.md
│   ├── 03_DATABASE_SCHEMA.md
│   ├── 04_ALGORITHMS.md
│   ├── 05_COMPETITIVE_RESEARCH.md
│   ├── 06_SECURITY_PRIVACY.md
│   ├── 07_TESTING_AND_DATA.md
│   ├── 08_UI_UX_SPEC.md
│   ├── 09_THREE_DAY_EXECUTION.md
│   └── 10_RESEARCH_AND_SOURCES.md
└── docs\            (this directory, created during analysis)
```

There is:
- No git repository (not initialized).
- No `frontend/` directory.
- No `backend/` directory.
- No `docker-compose.yml`, `.env.example` or `README.md`.
- No package manifests (`package.json`, `pyproject.toml`, `requirements.txt`).
- No database or migrations.
- No tests.

## 2. Existing Technologies

No technologies are present in the repository. The environment has:

| Tool       | Version                |
|------------|------------------------|
| Python     | 3.14.3                 |
| Node.js    | 24.13.1                |
| npm        | 11.19.0                |
| Docker     | 29.7.2                 |
| git        | 2.52.0                 |

Python 3.14 is available; the backend will target Python 3.12+ compatible libraries
(Pydantic v2, SQLAlchemy 2.x, FastAPI) — verify compatibility with 3.14 during STAGE A.

## 3. Existing Working Features

None. No application code exists.

## 4. Existing Incomplete Features

None. (Nothing has been started.)

## 5. Existing Technical Debt

None (greenfield). The only "debt" would be any inconsistency between the two
descriptions of the domain in the directive versus the research docs (see §12 below and
`DECISIONS.md`).

## 6. Specification Requirements

The specification defines a **modular monolith** prototype, "CleanSport Intelligence":

- **Frontend:** React + TypeScript + Vite + Tailwind + shadcn/ui + React Router +
  TanStack Query + Zustand + React Hook Form + Zod + Recharts + React Flow + Lucide.
- **Backend:** FastAPI + Pydantic + SQLAlchemy + Alembic + scikit-learn.
- **Database:** PostgreSQL (relational; no graph database — graph views derived from
  relational joins).
- **Deployment:** Docker Compose (`frontend`, `backend`, `postgres`); `.env.example`.

### Core domain areas

1. **Identity & Access** — users, roles, permissions, RBAC, audit.
2. **Subjects** — athletes, support personnel, teams, organizations, providers.
3. **Intelligence** — sources, reports, assessments, tags, relationships, ingestion,
   validation, normalization, entity resolution, deduplication.
4. **Events** — testing, biological observations, whereabouts, travel, medical/TUE,
   supplements.
5. **Analytics** — deterministic rules, feature engineering, Isolation Forest anomaly,
   temporal correlation, cross-source correlation, network analysis, explainable
   composite priority score. All reproducible/versioned.
6. **Alerts** — generation from thresholds/correlations/network clusters, triage,
   review, false-positive handling, conversion to case.
7. **Investigations** — cases, assignments, notes, tasks, actions, findings, timeline,
   relationship graph.
8. **Evidence** — first-class entity, links, metadata, hash where implemented.
9. **Reporting** — structured investigation reports, preview, export where practical.
10. **AI Assistant** — retrieval-grounded decision support with deterministic fallback.
11. **Outcomes / Audit** — case outcomes and security-sensitive auditing.

### Domain boundary (non-negotiable)

The system must **never** claim to determine guilt, output a "doping probability,"
issue autonomous sanctions, or produce an automatic ADRV determination. Outputs are
investigative signals and prioritization, reviewed by humans. This applies to DB model
names, API names, UI copy, prompt content and reports.

### Synthetic data targets

500 athletes / 80 support personnel / 40 teams / 30 providers / 100 supplements /
5,000 testing events / 4,000 whereabouts / 3,000 travel / 1,500 medical·TUE /
2,000 intelligence reports / 1,500+ relationships. Fixed seed. Known scenarios
(Normal → CRITICAL, plus False-Positive, Duplicate, Unreliable-source).

### Required synthetic scenarios

1. Normal (LOW)
2. Single statistical anomaly (LOW/MODERATE)
3. Repeated temporal signal (MODERATE/HIGH)
4. Longitudinal anomaly (HIGH)
5. Multi-source corroboration (HIGH/VERY HIGH)
6. Network cluster (VERY HIGH/CRITICAL)
7. False positive (alert → human → FALSE_POSITIVE)
8. Duplicate intelligence (dedupe)
9. Low-quality source (reduced priority)

## 7. Requirement-to-Code Mapping

See `docs/TRACEABILITY.md` for the full, living traceability matrix. The high-level
mapping:

| Domain area | Backend module | Frontend feature | DB entities |
|---|---|---|---|
| Auth/RBAC | `app/security/`, `app/api/auth` | `features/auth` | users, roles, permissions, role_permissions |
| Intelligence | `app/intelligence/` | `features/intelligence` | sources, intelligence_reports, source_assessments, intelligence_tags, intelligence_relationships |
| Subjects | `app/athletes/`, `app/entities/` | `features/athletes` | athletes, support_personnel, teams, organizations, providers |
| Events | `app/athletes/` | athlete profile tabs | testing_events, biological_observations, whereabouts_events, travel_events, medical_events, supplement_events |
| Analytics | `app/analysis/` | `features/analysis` | indicators, analysis_runs, feature_snapshots, anomaly_results, rule_results, correlation_results, network_results, priority_scores, model_versions, rule_versions |
| Alerts | `app/alerts/` | `features/alerts` | alerts, alert_signals, alert_reviews |
| Investigations | `app/investigations/` | `features/investigations` | investigations, investigation_assignments, investigation_notes, investigation_tasks, investigation_actions, investigation_findings |
| Evidence | `app/evidence/` | evidence module | evidence_items, evidence_links, evidence_metadata |
| Relationships | `app/relationships/` | `components/graph` | entity_relationships, relationship_types |
| Reporting | `app/reports/` | `features/reports` | investigation_reports, report_versions |
| Outcomes | `app/investigations/` | case workspace | case_outcomes |
| Audit | `app/audit/` | admin/audit | audit_events |

## 8. Missing Components

Since the repository is empty, **everything** is missing. Priority of build-out follows
the stage plan in §14 and the P0/P1/P2 classification from
`00_MASTER_SPECIFICATION.md` (P0 = required for end-to-end demo).

## 9. Architecture Conflicts

Two schemas describe overlapping but not identical domain tables:

| Area | Directive §12 name | Research `03_DATABASE_SCHEMA.md` name |
|---|---|---|
| Intelligence report | `intelligence_reports` | `intelligence_reports` (same) |
| Investigation notes | `investigation_notes` | `investigation_notes` (same) |
| Evidence | `evidence_items` + `evidence_links` + `evidence_metadata` | single `evidence` table |
| Relationships | `entity_relationships` + `relationship_types` | single `relationships` table |
| Case findings | `investigation_findings` | (not present in research schema v1) |
| Alerts signals | `alert_signals` | (not present in research schema) |

**Resolution:** The implementation will merge the two into a coherent superset. Where
the directive is more explicit (evidence sub-tables, alert signals, findings,
assignments), the directive takes precedence because it is the master engineering
directive. See `DECISIONS.md` entry D-001.

Other ambiguity: the directive's navigation lists **Reports** and **Analytics** as top
level and adds **Athletes**; the UI research doc lists **Graph** and **Resources**.
Resolution: prioritize directory-vs-UI requirement. The directive §38 is authoritative
for navigation; a Graph/Relationship view is embedded within investigations and athlete
pages rather than a separate top-level section (recorded in `DECISIONS.md` D-002).

## 10. Dependency Gaps

None present (greenfield). Planned dependencies:

- **Backend:** fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, alembic,
  psycopg (v3) / psycopg2-binary, scikit-learn, numpy, pandas, python-jose[cryptography],
  passlib[bcrypt] (or bcrypt directly — see `DECISIONS.md` on Python 3.14/passlib
  compatibility), httpx, pytest, pytest-asyncio, python-multipart (uploads).
- **Frontend:** react, react-dom, react-router-dom, @tanstack/react-query, zustand,
  react-hook-form, zod, @hookform/resolvers, recharts, @xyflow/react (React Flow),
  lucide-react, tailwindcss, vite, typescript, shadcn/ui (radix primitives).

## 11. Database Gaps

None present. Full schema to be created via Alembic migrations in STAGE A/B. PostgreSQL
required; connection via Docker Compose service `postgres`.

## 12. Security Gaps

None present (no code). Planned security baseline:

- Passwords hashed (never plaintext).
- JWT access tokens with expiry; logout/revocation strategy.
- Backend-enforced RBAC (4 roles) — frontend visibility is not authorization.
- Pydantic input validation; parameterized ORM queries.
- Confidentiality classification (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) with
  role-gated access to restricted records.
- Comprehensive audit events.
- Synthetic data only (no real personal/medical/financial/confidential-source data).
- Secrets via environment variables only; `.env.example`; never commit secrets.
- AI grounded in retrieved records only; deterministic fallback; no autonomous action.

## 13. Testing Gaps

None present. Planned coverage (per `07_TESTING_AND_DATA.md` + directive):

- **Unit:** normalization, entity resolution, rule engine, feature engineering, anomaly
  normalization, temporal & cross-source correlation, network scoring, priority scoring.
- **API:** authentication, authorization/403s, CRUD, alert review, investigation
  creation, evidence, reports.
- **Integration:** database → repository → service → API.
- **End-to-end:** synthetic intelligence → analysis → alert → triage → investigation →
  evidence → task → report → outcome → audit.
- **Analytical tests:** reproducibility, score ranges, ranking consistency, known
  scenario separation, false-positive handling, explanation consistency.

## 14. Recommended Implementation Order

Sequential stages (validate after each — see directive §62):

1. **STAGE A — Repository + foundation** — scaffolding, config, DB, migrations, auth,
   RBAC, application shell, dev containers.
2. **STAGE B — Domain model** — entities, relationships, repositories, services, APIs.
3. **STAGE C — Synthetic data** — generator, scenarios, `seed-data` / `reset-data`.
4. **STAGE D — Intelligence** — ingestion, normalization, entity resolution, inbox,
   athlete profile.
5. **STAGE E — Analytics** — features, rules, ML, correlations, network, priority.
6. **STAGE F — Alerts** — generation, triage, review, conversion.
7. **STAGE G — Investigations** — cases, assignments, evidence, tasks, notes, findings,
   timeline, graph.
8. **STAGE H — AI** — retrieval, summary, questions, report assistance, fallback.
9. **STAGE I — Reporting** — creation, preview, export where practical.
10. **STAGE J — QA** — tests, security checks, workflow verification, docs, cleanup.

---

*See also: `TRACEABILITY.md`, `DECISIONS.md`, `IMPLEMENTATION_STATUS.md`.*
