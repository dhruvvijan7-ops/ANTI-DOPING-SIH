# VERITY — Phases F–H Completion Report

Frontend build-out for the VERITY anti-doping platform: premium 13-section landing page
(F), authenticated investigator application (G), and verification/delivery (H).

All measurements and test counts below were taken from the live workspace on this machine
(Windows 11, Node v24.13.1/npm 11.19.0, Docker Desktop Linux containers) against the real
backend (`127.0.0.1:8015` for dev, `verity-backend:8000` behind nginx for the served build).
Nothing is invented; values without an instrumented measurement are reported as "not measured".

---

## 1. Frontend Architecture

Exact structure (`frontend/src`):

```
src/
├── main.tsx                  # React root, TanStack Query client, Router, ErrorBoundary
├── App.tsx                   # Route table (React Router 6, all route chunks lazy)
├── index.css                 # Tailwind layers, focus-visible, prefers-reduced-motion
├── vite-env.d.ts
├── components/
│   ├── auth/RequireAuth.tsx  # JWT gate; redirects to /login?from=…
│   ├── layout/AppShell.tsx   # Sidebar + topbar + <main id="main">, RBAC-filtered nav
│   └── ui/ …                 # badge, button, card, checkbox, dialog, dropdown,
│                             # error-boundary, field, progress, spinner, states
│                             # (PageLoading/Spinner/Skeleton/SkeletonRows), table,
│                             # tabs, toasts
├── features/
│   ├── alerts/TriagePanel.tsx        # Convert/dismiss/review flow on alert detail
│   ├── investigation/InvOverview, InvTimeline, InvEvidence, InvFindings, InvTasks,
│   │                 InvNotes, InvRelationships, InvIntelligence, InvAi, InvReports,
│   │                 InvAudit.tsx     # All 11 workspace tabs
│   └── relationships/RelationshipGraph.tsx   # Custom force-free SVG graph layout
├── lib/
│   ├── api/client.ts          # fetch wrapper, token attach, 401 session clear,
│   │                          # buildQuery (skips null/undefined/""), ApiError
│   ├── api/endpoints.ts       # 1-to-1 typed endpoint functions
│   ├── api/queries.ts         # useQuery/useMutation hooks (TanStack Query)
│   ├── api/types.ts           # backend contract types
│   ├── constants.ts           # status/level label maps, severity tones
│   ├── nav.ts                 # NAV + PERMISSIONS registry (drives shell + RBAC)
│   └── utils.ts               # cn, clamp, titleCase, initialsOf, truncate,
│                              # formatScore/formatIso/formatDate/timeAgo/formatBytes/
│                              # formatPercent, sortedKeys
├── pages/                     # Landing, Login, Dashboard, Intelligence, AlertDetail,
│                              # Alerts, Athletes, AthleteDetail, Investigations,
│                              # InvestigationWorkspace, Relationships, Reports, Audit,
│                              # AiAssistant, Users, NotFound
├── stores/auth.ts             # Zustand; persists {token,user} to sessionStorage
│                              # under key "verity.session"
└── test/setup.ts              # jsdom + jest-dom + API mocks
```

Decisions of note:

- **No heavy chart/graph/date libraries.** The relationship graph is a purpose-built SVG
  layout (~600 lines, no React Flow dependency); dates are formatted with a small local
  formatter. This keeps the eager bundle at 83 kB gzip.
- **Route-level code splitting.** Every page is `React.lazy`; only `index.tsx` (app shell,
  ui kit, api layer) is eager. The Landing route pulls its 27.89 kB chunk only when visited.
- **UI-state-only Zustand.** Server state lives in TanStack Query (cache invalidation on
  mutations); the auth store is the single persisted exception (sessionStorage).
- **All API access through typed endpoint functions** (`endpoints.ts`) consumed exclusively
  by hooks in `queries.ts`; components never call `fetch` directly.

## 2. Routes

| Path | Element | Lazy chunk |
|---|---|---|
| `/` | Landing | `Landing-*.js` |
| `/login` | Login | `Login-*.js` |
| `/dashboard` | Dashboard | `Dashboard-*.js` |
| `/intelligence` | Intelligence | `Intelligence-*.js` |
| `/alerts` | Alerts | `Alerts-*.js` |
| `/alerts/:alertId` | AlertDetail | `AlertDetail-*.js` |
| `/athletes` | Athletes | `Athletes-*.js` |
| `/athletes/:athleteId` | AthleteDetail | `AthleteDetail-*.js` |
| `/investigations` | Investigations | `Investigations-*.js` |
| `/investigations/:investigationId/*` | InvestigationWorkspace (11 tabs) | `InvestigationWorkspace-*.js` |
| `/relationships` | Relationships | `Relationships-*.js` |
| `/reports` | Reports (global index) | `Reports-*.js` |
| `/audit` | Audit | `Audit-*.js` |
| `/ai` | AiAssistant | `AiAssistant-*.js` |
| `/users` | Users (gated `users:manage`) | `Users-*.js` |
| `/404`, `*` | NotFound / redirect | `NotFound-*.js` |

All routes except `/` and `/login` are wrapped in `RequireAuth` (redirect to
`/login?from=…` when no token).

## 3. Landing Page

13 sections: **Hero#top → Problem → Pipeline → Signals → Priority → Workflow →
Humans → AI → Integrity → FAQ → CTA#cta**, wrapped in a sticky header (desktop anchor nav +
accessible mobile menu) and a footer.

- **Visual system:** editorial serif display (`--font-serif: Georgia`) for headlines vs.
  Inter body; ink/paper palette (`ink-950` on `paper-50`); single accent `signal-600`;
  oversized rules and whitespace; full-width dark sections for humans/integrity contrast.
- **Animation:** subtle scroll-driven header (border + backdrop-blur when scrolled),
  guardrail-strip count-up numbers, hover lifts, FAQ open/close with rotating "+". No
  framer-motion — CSS transitions only.
- **Responsive:** single-column on mobile with a hamburger menu (accessible toggle,
  `aria-expanded`); multi-column grids scale from 1→3 columns; sticky header adapts to
  anchored section nav (hidden on <md, mobile menu substituted).
- **Performance approach:** lazy route chunk, no hero videos/images (SVG-only decorative
  artwork, `aria-hidden`), system font fallbacks, no third-party scripts.

Copy discipline enforced by tests: priority scores are "lead strength", never a verdict;
hero states the platform "never [makes] a verdict about an athlete".

## 4. Application — Completed Modules

All authenticated modules are data-driven against the real backend:

- **Dashboard** — metrics + quick links to each module; backend `/dashboard` aggregate.
- **Intelligence** — paginated report list w/ filters (info category, reliability label,
  type, source), detail view.
- **Alerts** — list (filterable), **detail with “Why flagged?”** (score decomposition,
  signal features), **triage panel** (review / dismiss / false-positive / escalate /
  **convert to investigation** with priority + note).
- **Athletes** — list, **profile** with tests, ABP observations, whereabouts, travel,
  events timeline, intelligence, relationships.
- **Investigations** — list (status/assigned filters), **workspace with 11 tabs**:
  Overview, Timeline, Evidence (add/edit + integrity + versions + delete), Findings
  (CRUD + evidence links), Tasks, Notes, Relationships graph, Intelligence, **AI
  assistant** (grounded summaries/explanation/gaps/questions/report draft with typed
  claims + "sources come only from this case"), Reports (create/draft/publish),
  Audit trail.
- **Relationships** — global relationship list w/ filter.
- **Reports** — global report index.
- **Audit** — global audit-log browser.
- **AI Assistant** — global assistant entry point.
- **Users** — role/permission administration (RBAC-gated).
- **Login / Logout / NotFound** — JWT login flow; logout calls the backend, clears the
  query cache **and the local session** (sessionStorage), then redirects to `/login`.

## 5. API Integration

All endpoints below are wired through `endpoints.ts` (typed return contracts) and consumed
by hooks in `queries.ts`. `/api/v1` prefix in dev (`vite.config.ts` proxy → `127.0.0.1:8015`)
and production (nginx `location /api/` → backend:8000).

- Auth: `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`; Users: `GET /users`,
  `/users/roles`, `/users/permissions`
- Dashboard: `GET /dashboard`
- Alerts: `GET /alerts`, `GET /alerts/{id}`, `PATCH /alerts/{id}/status`,
  `POST /alerts/{id}/review|dismiss|false-positive|escalate|convert`
- Intelligence: `GET /intelligence/reports`, `GET /intelligence/reports/{id}`
- Athletes: `GET /athletes`, `GET /athletes/{id}`, `…/{id}/tests|abp|whereabouts|travel|events|intelligence|relationships`
- Investigations: `GET|POST /investigations`, `GET|PATCH|POST|CLOSE /investigations/{id}`,
  `…/{id}/intelligence|timeline|relationships|audit|assign`
- Evidence: `GET|POST /investigations/{id}/evidence`, `GET|PATCH|DELETE …/evidence/{eid}`,
  `…/evidence/{eid}/versions`
- Tasks/Notes/Findings: `…/{id}/tasks|notes|findings` CRUD + finding↔evidence link/unlink
- Reports: `GET|POST …/reports`, `PATCH|POST …/reports/{rid}[/publish]`
- AI: `POST …/ai/summary|timeline-summary|signal-explanation|information-gaps|questions|report-draft`
- Analysis: `POST /analysis/runs`, run list/detail, features/rules/anomalies/
  correlations/network/priority, `GET /analysis/subjects/{id}/results`
- Relationships: `GET /relationships`, `GET /relationships/{id}`
- Support persons: `GET /support-persons`, detail + relationships + intelligence

## 6. Authentication

Implemented flow:

- `Login.tsx` posts `{username,password}` to `POST /auth/login`; on success the
  `TokenResponse` (token + full user with role permissions) is stored via
  `useAuthStore` into **sessionStorage `verity.session`** (zustand persist, synchronous
  rehydration).
- `RequireAuth` gates all dashboard routes: no token → `Navigate to /login?from=…`;
  after login the return route restores.
- `api()` attaches `Authorization: Bearer …` on every request; a `401` clears the session
  (forcing a redirect to login). Network failures surface typed `ApiError`s.
- Logout: `POST /auth/logout`, then **query-cache clear + `clearSession()`** and
  navigation to `/login`. This ordering bug (session never cleared locally) was surfaced
  by the Playwright journey and fixed.
- RBAC is enforced twice: backend permissions are the source of truth; the shell filters
  `NAV` entries with `hasPermission(n.permission)` (e.g. Users requires `users:manage`,
  which only ADMINISTRATOR holds, so `/users` is hidden and unreachable for other roles).

## 7. Performance

Instrumented with Playwright/Chromium against the **nginx-served production build**
(`http://127.0.0.1:8080`, gzip on), developer defaults, loopback connection. Three cold
runs per route; medians below. No Lighthouse/field data was run.

| Metric | Landing (public) | Dashboard (authenticated) |
|---|---|---|
| TTFB | 2.3 ms (loopback nginx) | 1.3 ms (client-side nav) |
| FCP | 44 ms | 36 ms |
| LCP | 96 ms | 76 ms |
| CLS | 0 | 0.003 |
| INP | not measured (needs real user gestures; synthetic clicks are excluded by `PerformanceObserver`) |
| Initial requests | 6 (5 JS + 1 CSS) | 9 (7 JS + 1 CSS + favicon) |
| Transferred bytes | ~113 kB gzip | ~111 kB gzip |

These loopback figures are transport-bound; the portable numbers are bundle/request counts.
On real deployments TTFB is dominated by network, so treat ms values as "local best case".

Bundle size — production build (`vite build`, 1677 modules, built in 2.34 s):

| Chunk | Raw | gzip |
|---|---|---|
| `index-es-*.js` (eager shell) | 265.31 kB | 83.38 kB |
| `InvestigationWorkspace-*.js` | 41.04 kB | 10.22 kB |
| `Landing-*.js` | 27.89 kB | 8.17 kB |
| `AlertDetail-*.js` | 15.07 kB | 4.80 kB |
| `AthleteDetail-*.js` | 9.93 kB | 2.45 kB |
| `InvAi-*.js` | 6.77 kB | 2.35 kB |
| `Intelligence-*.js` | 5.71 kB | 2.10 kB |
| every other lazy page | 0.5 – 5.2 kB | 0.36 – 2.25 kB |

Design choices behind the numbers: route-level `React.lazy`, no chart/date/animation
libraries, SVG-only artwork on the landing page, nginx static caching
(`Cache-Control: public, max-age=2592000, immutable` on hashed assets).

## 8. Accessibility

Checks actually performed (no automated axe run in this phase):

- **Landmarks/keyboard:** skip links added to both `Landing` (`→ #top`) and `AppShell`
  (`→ #main`, `sr-only focus:not-sr-only`); `<nav aria-label="Landing sections">`,
  `aria-label="Main navigation"`, mobile toggle with `aria-expanded`;
  `<main id="main">` landmark.
- **Semantics:** account menu uses `role="menu"`/`role="menuitem"`; workspace sections
  use `role="tablist"`/`role="tab"`; decorative svgs `aria-hidden`.
- **Focus styles:** global `:focus-visible` outline (`signal-600`, offset 2 px).
- **Motion:** `@media (prefers-reduced-motion: reduce)` disables animation/transition and
  smooth scrolling globally.
- **Labels:** form controls use `Field`/`Label` associations; the alert-convert dialog
  fields were given IDs (`convert-title`, `convert-priority`, `convert-note`) and are
  asserted in tests to be reachable by label/role.
- **Color:** status never communicated by color alone — severity labels and text are
  always the primary signal (verified by code review in alerts/intelligence views).
- Tests assert landmark/anchor targets (`#top`, `#cta`, …) and accessible names for the
  primary CTAs.

Known gaps: no axe/pa11y automation job, no dedicated contrast audit report, dropdown
menu does not trap focus (opens on click, closes on outside-click/Escape).

## 9. Testing

| Suite | Result |
|---|---|
| Vitest (unit) | **42 passed / 0 failed** across 6 files |
| RTL (component) | included in the 42 (TriagePanel, Landing) |
| Playwright E2E | **1 passed / 0 failed** — critical journey: landing → login → dashboard → alerts → why flagged → workspace → AI assistant → audit → logout |
| Backend regression | **121 passed / 0 failed** (full `pytest` suite, exit 0, run in-container against compose postgres) |
| Typecheck | `tsc -b` clean |
| ESLint (flat) | 0 errors, 4 warnings (react-refresh in `toasts.tsx` only) |
| Production build | `vite build` success, 1677 modules |

The E2E test caught a real regression (logout never cleared the local session) and two
UI ambiguity bugs (duplicate “Sign out” elements, duplicate CASE_REF text).

## 10. Docker

Actual commands and results:

- `docker compose build` → OK. Backend image (`antidoping-backend`, python:3.12-slim),
  frontend image (`antidoping-frontend`, node:20-alpine build stage → nginx:1.27-alpine).
- `docker compose up -d --build` → OK. Services renamed to `verity-postgres`,
  `verity-backend`, `verity-frontend` (postgres volume name unchanged, seeded data intact).
- Health: `GET http://localhost:8080/api/v1/health` → `{"status":"ok","database":"ok"}`.
- Same-origin login through nginx: `POST http://localhost:8080/api/v1/auth/login` → 200
  with a JWT (nginx `location /api/` → backend:8000).
- Landing served: `GET /` → 200.
- The `frontend` nginx config adds SPA fallback (`try_files … /index.html`) and immutable
  caching for hashed assets. GZIP on for text/json/js/css/svg.

## 11. Known Limitations

- **Backend telemetry branding:** `/api/v1/health` still reports `"app":"CleanSport
  Intelligence API"` and JWT issuer/audience are `clean-sport-*`. The frontend never
  renders these; changing backend branding strings is out of scope for Phase F–H.
- **Default admin password:** `INITIAL_ADMIN_PASSWORD` must be set to a unique strong value;
  the legacy published default is explicitly denied in production and has been removed from
  templates, code defaults and documentation.
- **Playwright E2E is a single critical journey** (1 spec) — module-by-module flows are
  covered only by the unit/component layer and by manual verification.
- **INP not measured** (see §7) — requires real-user field instrumentation.
- **No automated axe scan** — §8 accessibility is manually/review-verified.
- **Relationship graph** is a custom SVG layout, not React Flow (JSON contract from the
  backend is honored; a React Flow skin could be added without contract changes).
- **Dev/prod API duality:** Vite dev proxies to `127.0.0.1:8015`; the served build uses
  the nginx proxy. Both verified, but they are separate configs.
- **`crypto.randomUUID` not polyfilled** where used — supported in all target evergreen
  browsers (not IE).
- Legacy container name `cleansport-postgres` was removed during the rename; its data
  volume persisted and is reused by `verity-postgres` (no data loss).

## 12. Phase I/J Readiness

Exactly what remains for the final two phases:

- **Stage I (Reporting):** print/PDF export ("Export (where feasible)" is `NOT_STARTED` in
  `IMPLEMENTATION_STATUS`); a shared report *preview* already exists in the workspace
  (`InvReports`), but a dedicated standalone preview route/rendering TLC and any
  export/print stylesheet are outstanding.
- **Stage J (QA & docs):** `docs/API.md` and `docs/DATA_DICTIONARY.md` are `NOT_STARTED`;
  no CI pipeline wiring for the frontend tests (Vitest/Playwright) though scripts exist
  (`npm run test`, `npm run test:e2e`); no scheduled/automated performance measurement;
  automation: add axe-based a11y job and a Lighthouse CI budget; review: expand the
  Playwright suite from one journey to per-module specs.
- **Demo workflow (directive §66):** verified manually end-to-end; codifying it as an
  additional annotated Playwright spec (checked against the §66 checklist) is the final
  verification deliverable.