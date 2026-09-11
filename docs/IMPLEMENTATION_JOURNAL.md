# Implementation Journal

Maintained per master-prompt §1009. Each entry records **date, phase, change, reason,
files changed, migration, API changes, frontend changes, tests, known limitations**.

---

## Gate 1006 — OSINT subsystem

**Date:** 2026-09-11  
**Phase:** Checkpoint 1006 (GO/NO-GO: AFTER OSINT)

### Change
Built a genuine OSINT subsystem: connector abstraction (GDELT, generic RSS, generic
web_doc), source registry with health/rate limiting, provenance-keeping raw records,
deduplication/syndication clustering, analyst claims, promotion into intelligence, RBAC
gates (`osint:read|collect|admin`), full API, React page, and tests. Mirrors master
prompt §29–§54, §69, §240–§254, §312, §405, checkpoint 1006.

### Reason
The current VERITY audit explicitly established there was no real external ingestion and
no OSINT subsystem (§29). The deliverable requires real public-source collection with
provenance and dedupe, not a fake "OSINT" label.

### Files changed
- New backend:
  - `backend/app/models/osint.py` — OsintSource, OsintRecord, OsintMention, OsintClaim.
  - `backend/app/osint/common.py` — SSRF guard, token-window rate limiter, SHA-256 content
    hash, extraction helpers.
  - `backend/app/osint/connectors/{base,gdelt,rss,web_doc,registry}.py`
  - `backend/app/osint/seeds.py` — default real source registry + idempotent seeding.
  - `backend/app/osint/service.py` — collection pipeline, dedupe/syndication, health
    machine, mentions, claims, promotion.
  - `backend/app/api/routes/osint.py`; registration in `backend/app/api/router.py`.
  - `backend/migrations/versions/0009_osint_gate.py`
- Modified backend:
  - `backend/app/security/rbac.py` (+OSINT_READ/COLLECT/ADMIN),
    `backend/app/db/seed.py` (role→permission map, calls `seed_default_osint_sources`),
    `backend/app/api/routes/intelligence.py` (`intel_summary` adds OSINT provenance
    fields), `backend/tests/conftest.py` (truncate osint tables).
- Tests: `backend/tests/test_osint_gate.py` (25 tests).
- Frontend:
  - `frontend/src/lib/api/types.ts` (OSINT contracts; `PERMISSION_KEYS` 29→32),
    `frontend/src/lib/api/endpoints.ts` (`osintApi`),
    `frontend/src/lib/api/queries.ts` (OSINT React Query hooks),
    `frontend/src/lib/nav.ts` (+osintRead/Collect/Admin; DROP_PERMISSIONS.osintRead),
    `frontend/src/components/layout/AppShell.tsx` (nav entry), `frontend/src/App.tsx`
    (lazy `/osint` route),
    `frontend/src/pages/Osint.tsx` (page), `frontend/src/pages/Osint.test.tsx` (5 tests).

### Migration
`0009_osint_gate` — applied to the test DB via `alembic upgrade head`. Tables:
`osint_sources`, `osint_records`, `osint_mentions`, `osint_claims`; indexes on
content hash, canonical URL, published/retrieved dates, source refs, syndication group.

### API changes
New endpoints under `/osint/*` (connector-types, sources CRUD + health + defaults,
per-source collect, targeted collect, records list/detail, dedupe-cluster, promote,
claims create/review). Promote requires `intelligence:create`; creation/review/registry
admin gated by `osint:admin`; collection by `osint:collect`; reads by `osint:read`.
`GET /intelligence/reports/{id}` response now carries OSINT provenance when promoted.

### Frontend changes
New `/osint` page (targeted collection, source registry + health, records explorer,
detail with provenance/mentions/claims, promote, dedupe cluster), nav entry, permission
keys, API client and hooks. Role view-only/collect/admin UI enforcement matches backend.

### Tests
- Backend: 25 new OSINT tests incl. the §312 connector failure matrix (success, duplicate,
  timeout, 429, 500, malformed, missing fields, bad URL) via a registered stub connector;
  **full suite 227 passed** (DB on `:54320`).
- Frontend: 5 new OSINT page tests; **full suite 79 passed**; `tsc -b` clean; ESLint 0
  errors; `vite build` green (Osint chunk emitted).

### Known limitations
- `nadaindia-site` default is disabled pending a stable public notices URL.
- No dark web/Tor/underground tooling (out of scope §44); no ADAMS/private-lab access
  claimed; no social connector shipped; Wayback/Common Crawl/commercial enrichment are
  architecture-only.
- `web_doc` extracts page text; link discovery, RSS discovery and search-history
  persistence (§245) remain future work.
- Live external smoke (GDELT, WADA RSS) pending against the deployed stack.