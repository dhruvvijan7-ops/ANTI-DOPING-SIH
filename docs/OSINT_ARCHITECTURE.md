# OSINT Architecture

Status: `VERIFIED` (backend suite 227 passed; frontend suite 79 passed, incl. 5 OSINT page
tests; production build green).

This document describes the open-source intelligence (OSINT) subsystem introduced for
master-prompt checkpoint 1006. It covers design, connector abstraction, the source
registry, collection, provenance, deduplication, claims, authorization, the API surface,
frontend integration and how each requirement in `VERITY_OSINT_REGISTER.md` is met.

Reference sections: master prompt §29–§54 (OSINT), §69 (rate limiting), §240–§254
(targeted collection / searches / claims), §312 (connector testing matrix), §405 (OSINT
register), §463 (real sources), gasgate checkpoint list 1006.

---

## 1. Design principles

1. **Real sources only.** The registry is *configuration* for real, existing public
   endpoints (`backend/app/osint/seeds.py`). No fabricated articles, no fictional APIs,
   no fake "social monitoring" (§31). Collection writes only what a live connector
   actually returns.
2. **Targeted, not exhaustive.** Collection is triggered per-source or via targeted
   cloud queries with terms + lookback (+ optional `source_ids`/`max_records`). The
   system never "collects everything" (§243).
3. **Provenance is mandatory.** Every raw record stores `source_url`, `canonical_url`,
   `publisher`, `author`, `published_at`, `retrieved_at`, `title`, content hash,
   `source_type`, `authority_level`, `extraction_method`, plus a reference to its
   `OsintSource` (§49, §50).
4. **Deduplication with a syndication lens.** A syndicated article copied by five
   publishers counts as one independent source (§51, §52).
5. **Respect the network.** Public, official, low-frequency endpoints; per-source rate
   limiting; SSRF guards; no bypassing of authentication or access controls (§43, §48,
   §69, §447-adjacent ethics clauses).
6. **Least privilege.** Three new OSINT permissions; UI mirrors backend enforcement.

## 2. Connector abstraction

`backend/app/osint/connectors/` implements `SourceConnector` (registry/base.py):

- `connector_type` — stable machine key (`gdelt`, `rss`, `web_doc`).
- `kind` — `"search"` (targeted queries) vs `"pull"` (single configured URL).
- `search_driven: bool` and optional `supports_search: bool` (GDELT is search-driven;
  RSS and web_doc are fetch-only).
- `probe(db, source)` — cheap validation request used by health checks.
- `fetch(db, source, limit=…)` — yields normalized `RawRecordItem`s.
- `search(db, source, terms, days, limit)` — targeted collection (GDELT only).
- `validate(json)` — connector-specific response validation (missing fields, bad
  payloads, empty responses).
- `domain()` — URL host for SSRF allow-list checks.

Concrete connectors:

| `connector_type` | Purpose | Endpoint family | Notes |
|---|---|---|---|
| `gdelt` | Global news / official authority monitoring | GDELT DOC 2.0 `https://api.gdeltproject.org/api/v2/doc/doc` | search-driven; `mode=artlist&format=json&sort=datedesc`; `timespan` from lookback days; query built from per-source `base_query`/`probe_query` in `extra_config`; results limited via `maxrecords` |
| `rss` | Generic RSS/Atom parsing | any RSS/Atom feed (default seed: WADA News) | one generic implementation, feedparser-driven; entries with upcoming publication dates dropped |
| `web_doc` | Single public HTML page | any public HTML page (seed: WADA News & Releases; NADA India root, disabled) | html.parser text extraction; links/sqespots deferred to the hierarchical search-driven layer |

Real seed sources (configuration only): GDELT Global (public news), GDELT Official
authority-domain filter (wada-ama.org, ita.sport, nadaindia.org, ndtl.nic.in), WADA News
RSS, WADA News & Releases page, and NADA India public notices (disabled until an operator
confirms a stable public notices URL). Seeding is idempotent
(`seed_default_osint_sources(db)`), invoked from `app.db.seed.run_seed` and from
`POST /osint/sources/defaults`.

## 3. Source registry and health (`app/models/osint.py`, `app/osint/service.py`)

`OsintSource` persists: `source_id` (unique user-friendly slug), name, `connector_type`,
url, `authority` (`OFFICIAL | PUBLIC_NEWS | PUBLIC_SOCIAL | ARCHIVAL | COMMERCIAL`),
`jurisdiction`, `enabled`, `poll_frequency_min`, `rate_limit_per_min`, `health`
(`ACTIVE | DEGRADED | FAILED | RATE_LIMITED | DISABLED`), `consecutive_failures`,
`last_success_at` / `last_failure_at` / `last_failure_reason`, and `extra_config`.

Health machine (`ensure_source_health`):

- A clean run after one or more consecutive failures → `DEGRADED` (recovery), next clean
  run → `ACTIVE`.
- Failure marks `FAILED` (or `RATE_LIMITED` when the connector reports
  `RateLimitedError`); `consecutive_failures` increments on each failure and resets on
  success.
- A disabled source reports `DISABLED` and is skipped by collection (toggle via
  `PATCH /osint/sources/{id}`).

Per-source rate limiting (`app/osint/common.py`) is a token-bucket windowsed limiter
(`O()` for `rate_limit_per_min`) enforced inside the service around connector calls; a
violation raises `RateLimitedError`.

SSRF guard (`app/osint/common.py`):

- URL protocol allow-list (`http`, `https`).
- Public host/hostname resolution disabled (no literal IPs, no `127.0.0.1`,
  `localhost`, `0.0.0.0`, link-local/loopback/unicast ranges; any resolved address in a
  private range is rejected).
- Redirect re-validation — same rules apply after each redirect hop.

## 4. Raw records, provenance, dedupe

`OsintRecord` stores §49 fields plus `language`, `jurisdiction`, `syndication_group`,
`terms_matched`, `is_duplicate`, `duplicate_reason` (`CONTENT_HASH`, `CANONICAL_URL`,
`SYNDICATION`, `SAME_SOURCE`), `duplicate_of`, `canonical_url`, `content_hash` (SHA-256
of normalized content), and `json` content. `OsintMention` links a record to entities
(`subject_type`, `subject_id`, `subject_label`, `match_kind EXACT|CONTAINS`) via a
lightweight matching dictionary.

Collection (`run_source_collection`) pipeline:

1. Rate-limit check → connector `validate` → `fetch` (or `search` for the targeted path).
2. `dedupe` returns per-item `(exists, is_syndication, reason, cluster)`.
3. New records are inserted with provenance; syndicated copies tagged
   `SYNDICATION` and grouped under a `syndication_group`; `mentions` extracted.
4. `_mark_source_success` / `_mark_source_failure` update health.
5. Returns a summary (ok, health, error, new/duplicates/mentions, stored list).

Promotion (`promote_to_intelligence`) converts an `OsintRecord` into an
`IntelligenceReport` (title, content, source, provenance JSON with
url/canonical_url/publisher/journal-author_id/retrieved_at/content_hash/osint_record_id),
returns the report id, and audits `intelligence.create-from-osint`. Promotion is a
deny-by-default separate permission (`INTELLIGENCE_CREATE`).

Claims (`OsintClaim`): a `{subject, predicate, object(string), confidence,
verification}` row recorded against a record by an analyst (`osint:admin`), with
`created_by`/`reviewed_by`/timestamps; verification statuses
`UNREVIEWED | REVIEWED | CORROBORATED | DISPUTED | REJECTED | PROMOTED_TO_EVIDENCE`.
A patent conflicts from differing sources are surfaced as `DISPUTED` rather than an
arbitrary winner (§250).

## 5. Authorization

New permissions in `app.security.rbac.Permissions`:

| Key | Roles granted | Enforced routes |
|---|---|---|
| `osint:read` | ADMIN, INVESTIGATOR, INTELLIGENCE_ANALYST, VIEWER | see-registry, connector types, records, record detail, dedupe cluster, source health |
| `osint:collect` | ADMIN, INVESTIGATOR, INTELLIGENCE_ANALYST | `POST /osint/sources/{id}/collect`, `POST /osint/collect` |
| `osint:admin` | ADMIN, INTELLIGENCE_ANALYST | source create/update/delete, seed defaults, claims create/review |

Promotion additionally requires `intelligence:create`. Route dependencies are registered
in `backend/app/api/routes/osint.py`; seed roles in `app.db.seed.py`.

## 6. API surface (`backend/app/api/routes/osint.py`, registered in `router.py`)

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/osint/connector-types` | osint:read | list connectors |
| GET | `/osint/sources` | osint:read | registry with filters (connector/authority/include_disabled/pagination) |
| POST | `/osint/sources` | osint:admin | register a source (config only) |
| PATCH | `/osint/sources/{source_id}` | osint:admin | update config / toggle enabled / rate limit |
| DELETE | `/osint/sources/{source_id}` | osint:admin | remove source (records retained) |
| GET | `/osint/sources/{source_id}/health` | osint:read | health for one source |
| POST | `/osint/sources/defaults` | osint:admin | idempotent seed of default registry |
| POST | `/osint/sources/{source_id}/collect` | osint:collect | collect a single source |
| POST | `/osint/collect` | osint:collect | targeted collection (terms, days, optional source_ids, max_records) |
| GET | `/osint/records` | osint:read | record list + filters (q, authority, date_from/to, include_duplicates, source_id, pagination) |
| GET | `/osint/records/{record_id}` | osint:read | record detail incl. provenance, mentions, claims |
| GET | `/osint/records/{record_id}/dedupe-cluster` | osint:read | syndication cluster (member_count, independent_sources, publishers, members) |
| POST | `/osint/records/{record_id}/promote` | intelligence:create | promote to intelligence |
| POST | `/osint/records/{record_id}/claims` | osint:admin | create claim |
| PATCH | `/osint/claims/{claim_id}` | osint:admin | review/verify claim |

`intelligence.py`'s `intel_summary` now includes OSINT provenance (`url`,
`canonical_url`, `publisher`, `retrieved_at`, `content_hash`, `osint_record_id`) when a
report originates from promotion, so origin is always traceable from the intelligence
layer (§50).

## 7. Frontend integration

`frontend/src/pages/Osint.tsx` (route `/osint`, lazy-loaded; nav item in AppShell under
`osint:read` view-gate):

- Targeted collection form (terms + lookback) with per-source result summaries —
  `useOsintCollectTargetedMutation`.
- Source registry list (health badges, authority badges, per-source `Collect`,
  enable/disable, remove) — `useOsintSourcesQuery`, `useOsintCollectSourceMutation`,
  `useOsintUpdateSourceMutation`, `useOsintDeleteSourceMutation`.
- Admin-only register-source form with real connector-option listing and "seed default
  sources" — `useOsintCreateSourceMutation`, `useOsintSeedDefaultsMutation`,
  `useOsintConnectorTypesQuery`.
- Records explorer (search / authority filter / include-duplicates), record detail with
  provenance, content preview, mentions, promote-to-intelligence button
  (`intelligence:create`), claims add/review panel (`osint:admin`), and dedupe-cluster
  panel — `useOsintRecordsQuery`, `useOsintRecordDetailQuery`,
  `useOsintDedupeClusterQuery`, `useOsintPromoteMutation`,
  `useOsintCreateClaimMutation`, `useOsintReviewClaimMutation`.

API client: `osintApi` in `frontend/src/lib/api/endpoints.ts`; typed contracts and
`osint:admin|collect|read` in `frontend/src/lib/api/types.ts` (`PERMISSION_KEYS` 32);
React Query hooks in `frontend/src/lib/api/queries.ts`; nav permission constants in
`frontend/src/lib/nav.ts`.

## 8. Testing

- `backend/tests/test_osint_gate.py` (25 tests): source CRUD/validation, defaults
  idempotency, collection + provenance + mentions, dedupe by content hash and canonical
  URL, syndication cluster main-body, health transitions (fail→`FAILED`/`RATE_LIMITED`,
  recovery→`DEGRADED`→`ACTIVE`), the §312 connector failure matrix (success, duplicate,
  timeout, 429, 500, malformed payload, missing fields, bad URL), rate limiting,
  per-source disabling, targeted collection, promotion with audit provenance,
  claims round-trip, SSRF guard, missing-connector error, RBAC 401s. A registered stub
  connector (`register_type("stub_news", StubConnector)`) drives the matrix without
  touching the network.
- Full backend suite: `227 passed` (run with test database on `:54320`).
- `frontend/src/pages/Osint.test.tsx` (5 tests): access restriction, sources+records
  load, per-source collect fires, promote fires with correct body, admin/collect actions
  hidden for read-only roles. Frontend suite: `79 passed`, typecheck clean, ESLint 0
  errors, `vite build` green (Osint chunk emitted).

## 9. Known limitations

- No dark-web / Tor / underground-market tooling (§44 — out of scope).
- No ADAMS or private government/laboratory access; NDTL/NADA connectors only use public
  material (§32–§34).
- Public social-media monitoring is designed in the authority model but no social
  connector ships yet (only permitted, non-access-control-evading public use is in scope
  §43).
- `nadaindia-site` seed default is disabled pending a stable public notices URL.
- Historical/archival (Wayback, Common Crawl) and commercial enrichment (OpenCorporates
  etc.) are architecture-only for now; no connectors ship.
- `web_doc` extracts page text; internal link/`RSS-discovery` enrichment and search
  history persistence (§245) are future work.