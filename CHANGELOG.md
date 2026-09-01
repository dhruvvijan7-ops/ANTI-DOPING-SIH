# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added
- Initial repository setup and version control (`.gitignore`, remote `main` branch).
- Repository documentation: README, CHANGELOG, CONTRIBUTING, LICENSE, CI workflow,
  GitHub issue/PR templates.
- `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/TESTING.md`, `docs/PROJECT_STATUS.md`.
- Domain validation pass (`docs/DOMAIN_VALIDATION.md`) covering 20 intelligence/
  investigation concepts against WADA ISII/ISTI, the IG Guidelines, ITA REVEAL and
  NADA India sources; decisions D-010..D-012.
- STAGE D/E/F Analytics Engine (backend):
  - 17 versioned feature computations (features.py).
  - 9 deterministic rules (RULES-001..RULES-009).
  - Isolation Forest anomaly detection with feature-level explanations.
  - Temporal (45-day) and cross-source (90-day) correlation with deduplication.
  - Network relevance scoring (degree, diversity, connected high-priority count).
  - Composite priority formula (0.25R+0.20A+0.20C+0.15T+0.10N+0.10S), 5 levels.
  - Analysis run orchestration (runner.py) with two-pass network and alert generation.
  - CLI runner: `python -m app.analysis.cli run`.
  - 11 analytics/alerts ORM tables (analysis_runs..alerts, alert_signals).
  - API routes: analysis runs, per-stage retrieval, subject results, alerts with traceability.
  - Migration 0002 with domain tables + CHECK constraints (Admiralty D-010).
  - 72 automated tests (features, rules, anomaly, correlation, network, priority, scenarios, API, auth, authz).
- Bug fixes:
  - `get_current_user` token injection: `Depends(oauth2_scheme)` was missing.
  - `InvalidCredentialsError` now returns HTTP 401 instead of 500.

## 0.1.0 — 2026-09-01

### Added
- STAGE A foundation:
  - FastAPI backend scaffold (`backend/app`) with config, logging, structured
    exception handling and request-id middleware.
  - Identity model: users, roles, permissions, `role_permissions`, audit events.
  - Authentication (login/logout/me) with JWT + bcrypt; server-validated RBAC
    (admin, investigator, intelligence analyst, viewer).
  - Audit-log service.
  - Alembic migration `0001_identity_security`.
  - Docker Compose (PostgreSQL 16 + backend; frontend service defined), `.env.example`.
- STAGE B domain models (written, migration pending):
  - Subjects: team, organization, support person, provider, supplement, athlete.
  - Intelligence: sources, reports, tags, source assessments.
  - Events: testing, biological, whereabouts, travel, medical, supplement.
  - Relationships: relationship types + entity relationships.
  - Scenarios: synthetic scenario registry.
- Backend tests: authentication and authorization.
- Living documentation: `DECISIONS.md`, `TRACEABILITY.md`, `IMPLEMENTATION_STATUS.md`,
  `IMPLEMENTATION_BASELINE.md`.