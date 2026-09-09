# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased (Landing page & authentication update)

### Added
- Cinematic landing intro: bare paper background → centered serif "VERITY" (word-in
  animation) → the scene zooms through the dot of the "I" (measured from the rendered
  dot with `getBoundingClientRect`, so it stays centered on any viewport) → overlay
  cut-to-landing. 1.76 s full timeline, ~240 ms reduced-motion path, plays once per
  session (`sessionStorage["verity.intro.seen"]`), skipped on hash/back/forward/deep-link
  navigation, `pointer-events-none` + `aria-hidden`, CSS-transforms only (no canvas/WebGL).
- Scroll-reveal animations: `Reveal` IntersectionObserver component wrapping the landing
  sections; nav clicks smooth-scroll (respecting `prefers-reduced-motion`), update the URL
  hash without adding history entries, close the mobile menu, and briefly emphasize the
  focused nav item. Section `id="pipeline"` renamed to `id="how-it-works"` (anchor + hero
  CTA updated).
- Self-service account creation (`POST /auth/register`): username regex `^[A-Za-z0-9_.-]+$`
  (min 3), password min 8, duplicate username or non-null duplicate email → 409, no DB
  constraint on email (uniqueness enforced at the API); grants the least-privilege `VIEWER`
  role, auto signs the user in (`last_login_at` updated), and audits `auth.register`.
- Password reset: `POST /auth/forgot-password` (identifier lookup, neutral "If an account
  exists…" response to avoid enumeration; SHA-256-hashed single-use tokens stored in the
  new `password_reset_tokens` table with 30-minute expiry and `used_at`; outstanding unused
  tokens invalidated on each new request; audits `auth.password_reset_requested`) and
  `POST /auth/reset-password` (one-time redemption, expiry + format checks → 400
  "Invalid or expired reset token", other unused tokens cleared, password updated and
  `password_updated_at` refreshed; audits `auth.password_reset` / `auth.password_reset.failed`).
  Dev builds echo a `dev_reset_token` for one-click reset testing; production never does
  (gated on `settings.is_production`).
- Frontend auth pages: shared `AuthShell` layout with auth-enter transition; rewritten
  `Login` (forgot-password + create-account links, `?reset=1` reset-confirmation banner);
  new `Signup`, `ForgotPassword` (neutral state + dev-only demo link), `ResetPassword`
  (token read from URL, missing-token and success states) pages with lazy routes
  `/signup`, `/forgot-password`, `/reset-password`.
- API layer: `authApi.register/forgotPassword/resetPassword` + typed request/response
  contracts.
- Tests: backend `test_auth.py` +23 (registration, duplicate username/email, weak password,
  forgot-password neutral/dev-token/email/production guards, reset full flow, single-use,
  expiry, invalid token, password updated) — full backend suite 144 passing; Vitest
  landing/auth tests (43 passing); Playwright E2E `e2e/landing-auth.spec.ts` (intro
  first-visit, reduced-motion path, no replay on hash nav, signup → dashboard → logout →
  forgot → dev reset link → reset → login with new password).
- Migration `0004_password_reset_tokens` (revises `0003_evidence_integrity`) applied to the
  dev database.
- ESLint self-review: 0 errors (5 warnings — 4 pre-existing toast react-refresh + 1 new
  `Reveal.tsx` react-refresh export warning, all non-fatal).

### Changed
- Bundle: landing chunk 32.09 kB / 9.67 kB gzip (baseline 27.89 / 8.17); index 266.39 kB /
  83.66 kB gzip. Cold-load perf re-measured via Playwright (nginx :8080): identical request
  count (6 landing / 9 dashboard), transfer +2.6 kB, FCP/LCP within noise — no actionable
  regression.
- Docker stack rebuilt for both new backend (`verity-backend`) and new frontend
  (`verity-frontend`, nginx :8080); dev backend on 127.0.0.1:8015 launded with
  `DATABASE_URL` pointing at host port 54320 (root `.env` keeps `DATABASE_URL` commented to
  stay compose-driven).

## Unreleased (Phase F–H frontend)

### Added
- Premium 13-section landing page (hero, problem, pipeline, signals, priority, workflow,
  humans, AI, integrity, FAQ, CTA) with accessible anchors, skip link, `prefers-reduced-motion`
  support and guardrail copy; route-level lazy chunk.
- Authenticated investigator application: dashboard, intelligence inbox, alert center with
  "why flagged" score decomposition + triage (review/dismiss/false-positive/escalate/convert),
  athlete profiles (tests/ABP/whereabouts/travel/events/intelligence/relationships),
  investigation workspace with 11 tabs (overview, timeline, evidence with integrity/versions,
  findings with evidence links, tasks, notes, relationships graph, intelligence,
  AI assistant, reports, audit), global reports/audit/relationships/ai index pages, and
  RBAC-gated users administration.
- Authentication flow: JWT login, session in sessionStorage (`verity.session`), 401
  auto-clear, guarded routes (`RequireAuth` with `?from=`), logout that clears query cache
  AND local session.
- API layer: typed endpoint functions, TanStack Query hooks, `buildQuery` query builder
  (skips null/undefined/empty values).
- Verification: 42 Vitest/RTL tests (6 files), Playwright E2E critical journey
  (`e2e/journey.spec.ts`), `tsc -b` + ESLint flat config (0 errors) + production build.
- Docker: `frontend/Dockerfile` (node build → nginx), `nginx.conf` with `/api` reverse
  proxy + SPA fallback + immutable asset caching, `.dockerignore`; compose services renamed
  to `verity-postgres` / `verity-backend` / `verity-frontend` (existing postgres data
  volume preserved).

### Changed
- Vite dev proxy retargeted to `http://127.0.0.1:8015`; `playwright.config.ts` webServer
  pinned to `--host 127.0.0.1 --port 5199`.
- Landing trust-strip copy tightened ("lead strength, not a judgement about guilt or
  innocence"); hero states the platform never renders a verdict about an athlete; colors
  are never the sole signal.
- Root `.env` / `.env.example` header rebranded to VERITY (credentials and postgres
  database name intentionally unchanged so the persisted volume keeps working).

### Fixed
- `useLogoutMutation` never cleared the local session (E2E found logout left the app
  signed in and bounced back to `/dashboard`).
- `index.html` `<link rel="preconnect" href="/" />` caused the production build to fail
  with EISDIR (Vite reading a directory); removed.
- Landing duplicated `Workflow` symbol (aliased `WorkflowIcon`) and removed an unused
  `Certificate` icon import.
- AppShell/Alerts used `useCan` inside callbacks violating the ESLint hooks rule;
  switched to direct store `hasPermission`.
- `RelationshipGraph` non-null assertion on `nodes[0]` for the single-node case.
- Removed unused `sentinel` helper and stale query hooks; `state.tsx` re-exports
  page-loading primitives; `infoCategoryLabel`/`reliabilityLabel` imports relocated to
  `@/lib/constants`.
- `nav.ts` `PERMISSIONS` gained `usersManage` (test-verified); `client.buildQuery`
  exported for tests.

### Added
- Case assignment (G4/D-018):
  - `POST /investigations/{id}/assign` to assign/unassign the case owner, gated by the
    previously-unused `INVESTIGATIONS_ASSIGN` permission (ADMINISTRATOR / INVESTIGATOR;
    analyst/viewer 403, anonymous 401). Same-assignee rebinding → 422; unknown user → 404.
  - `INVESTIGATION_ASSIGNED` audit entry with `previous_assignee` / `new_assignee` / `note`.
  - `assigned_to` query filter on the investigations list; `assigned_to_name` resolved on
    summaries and (for task rows) task summaries.
- Evidence integrity + authorization (G6/D-019):
  - Sensitivity levels `ROUTINE/SENSITIVE/HIGHLY_SENSITIVE/RESTRICTED`; items rated
    HIGHLY_SENSITIVE or RESTRICTED are hidden from list results and denied on detail (403)
    unless the caller holds `INVESTIGATIONS_MODIFY`.
  - Real, documented SHA-256 content integrity (`app/investigations/evidence_integrity.py`):
    canonical form `clean-sport-evidence-v1`, `\x1f`-joined immutable field order; recomputed
    on every response so tampering surfaces as `integrity.verified=False`.
  - Append-only version history (`evidence_versions`): a snapshot per mutation, unique
    per `(evidence_id, version_number)`, with `changed_by` + `change_reason`;
    `GET /investigations/{id}/evidence/{id}/versions`.
  - Controlled soft-delete (no hard delete endpoint): item is flagged `deleted_at`/`deleted_by`,
    removed from listings, version bumped, final snapshot appended, history and
    finding→evidence links preserved; versions endpoint 404s for deleted items by design.
  - Audited `EVIDENCE_CREATED` / `EVIDENCE_UPDATED` / `EVIDENCE_DELETED` events.
- Finding→evidence FK links (G6):
  - `FindingEvidenceLink` (finding FK CASCADE, evidence FK RESTRICT; unique per pair) with
    validity `SUPPORTING/CONTRADICTING/REVIEW`; link/unlink endpoints under
    `INVESTIGATIONS_MODIFY`. Cross-investigation evidence → 422, duplicate → 409,
    deleted evidence → 409, invalid validity → 422, missing evidence → 404.
  - `FINDING_EVIDENCE_LINKED` / `FINDING_EVIDENCE_UNLINKED` audit events.
- Migration `0003_evidence_integrity` (on top of `0002_investigations_reports`): evidence
  sensitivity/hash/version/deleted columns + `evidence_versions` + `finding_evidence_links`.
- Tests: `tests/test_investigation_hardening.py` (8 tests: assignment lifecycle+audit+filter,
  assignment permission enforcement, evidence sensitivity ACL, integrity+version history+
  tamper detection, soft-delete preservation, finding↔evidence links, link permissions,
  production-config guard). Full backend suite now 129 tests passing.
- Security guardrails (live-verified): production boot refuses to start when
  `JWT_SECRET_KEY` is a known dev default / shorter than 32 chars or `INITIAL_ADMIN_PASSWORD`
  is the documented default; `/docs`, `/redoc` and OpenAPI are disabled in production.

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
  - Migration 0002 with domain tables + CHECK constraints (5 Admiralty enums, D-010).
  - 72 automated tests (features, rules, anomaly, correlation, network, priority, scenarios, API, auth, authz).
- Bug fixes:
  - `get_current_user` token injection: `Depends(oauth2_scheme)` was missing.
  - `InvalidCredentialsError` now returns HTTP 401 instead of 500.

## Unreleased (G2/G3 synthetic + domain reads)

### Added
- Synthetic scenario runtime (STAGE C, G2/G3):
  - `app/data/registry.py`: stable 7-scenario catalog with ground-truth labels.
  - `app/data/generators.py`: fully deterministic generators (14 athletes, teams,
    orgs, providers, supplements, support persons, 8 sources incl. CONFIDENTIAL/
    RESTRICTED, relationships) plus per-scenario signatures.
  - `app/data/populate.py`: persistence, relationship-type resolution, scoped
    `TRUNCATE ... CASCADE` reset, `SyntheticScenario` registration (seed in `extra_refs`).
  - `app/data/cli.py`: `list` / `seed-registry` / `populate` / `reset`.
  - `docs/SYNTHETIC_DATA.md`.
- Domain read APIs (G3) — dashboard, subjects (athletes/support-person), intelligence
  reports with source redaction, relationships (all RBAC-gated).
- Repository fix: biological observations propagate baseline deviation into
  `Signal.value` so deviation features/rules match the in-memory contract for
  DB-persisted subjects.
- `tests/test_synthetic_scenarios_runtime.py`: catalog, determinism, persistence,
  reset, and per-scenario pipeline signal tests (qualitative only).
- `tests/test_domain_reads.py`: 20 tests for the new domain read endpoints.

## Unreleased (STAGE F/G/H/I)

### Added
- Alert triage (STAGE F): audited review/dismiss/escalate/false-positive endpoints and
  alert→case conversion (`POST /api/v1/alerts/{id}/convert`) that creates an
  investigation, preserves the originating alert context, and records `INVESTIGATION_CREATED`
  + `ALERT_CONVERTED` audit events. Triage metadata (`triaged_at`, `triage_meta_json`,
  `investigation_id`) added to `alerts`.
- Investigation workspace (STAGE G):
  - Models + migration `0002_investigations_reports` (investigations, evidence_items,
    investigation_tasks, investigation_notes, investigation_findings, investigation_reports).
    Priority/status validated at the application layer (Pydantic enums); the migration
    itself adds no CHECK constraints (verified via pg_constraint).
  - Case CRUD + close, overview (counts, originating alert, subject label), intelligence
    reference, mixed timeline (events/reports/case work) with `ALERT_SIGNAL` vs `CONTEXT`
    relevance, evidence/tasks/notes/findings management, case audit trail, and the
    relationshipl graph JSON contract for the React Flow visualizer ("association does
    not imply wrongdoing").
- Controlled AI decision support (STAGE H):
  - `AIService` abstraction with `LLMAIService` (OpenAI-compatible) and
    `DeterministicFallbackAIService`; app never depends on a vendor (selected via env).
  - Retrieval scoped to one case (`app/ai/retrieval.py`); output grounded, otherwise the
    exact phrase *"The available case records do not establish this."*; no guilt/sanction/
    invented-evidence conclusions; claims typed as RECORDED_FACT / ANALYTICAL_SIGNAL /
    INFERENCE / INVESTIGATIVE_QUESTION.
  - Operations: case summary, timeline summary, signal explanation, information gaps,
    investigation questions, report draft (`POST /investigations/{id}/ai/...`).
- Versioned reporting (STAGE I): report creation as v1 DRAFT, publish→FINAL, editing a
  FINAL report creates the next version and supersedes the old one; sections (metadata,
  purpose, intelligence, signals, timeline, relationships, evidence, findings, unresolved
  questions, outcome, audit metadata); author/created/version/status recorded per version.
- RBAC: INVESTIGATOR role granted `AUDIT_READ` (case audit trail access).
- Tests: `test_investigations_api.py` (4), `test_ai_reporting.py` (4), shared
  `tests/support_domain.py`; SQLAlchemy-side seeding isolated per test via autouse
  truncation; per-user `TestClient` fixtures.
- Bug fixes:
  - Test fixtures shared one `TestClient`, so multi-role tests silently leaked tokens
    (e.g. `viewer_client` overwrote `analyst_client`); each authed fixture now owns its
    client → latent `test_unauthenticated_can_read_runs` false-green corrected to
    `test_unauthenticated_cannot_read_runs` (401).
  - Anomaly Isolation Forest excluded relationship-graph features (scored separately by
    the dedicated network stage); previously a densely-connected subject read as "most
    normal" and the network scenario failed to outrank normal subjects
    (`test_network_scenario_outranks_normal`, deterministic 20.02 vs 21.47 failure).

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