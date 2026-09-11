# VERITY OSINT Register

Status: `REAL` — all rows are configuration for existing, live public endpoints. No
fabricated articles, no fictional APIs (§31). Collection writes only what connectors
actually fetch from these sources.

Columns per master-prompt §405:
**source** · **data** · **connector** · **limitations** · **provenance** · **retention**

---

## Default registry (seeded, `POST /osint/sources/defaults`)

| Source | Data | Connector | Limitations | Provenance | Retention |
|---|---|---|---|---|---|
| **GDELT Global News (anti-doping)** — `gdelt-global` · Tier 2 §39 | Public news matching `anti-doping OR doping OR performance-enhancing drugs` | `gdelt` (DOC 2.0 `api/doc`, artlist/json, datedesc, maxrecords, timespan) | Free-key GDELT 2.0 API; results may be delayed vs publication; news, not adjudication | `source_url`, canonical_url, publisher, author, `published_at`, `retrieved_at`, title, content hash, authority `PUBLIC_NEWS`, `extraction_method`, source_id | Records persist until administratively removed; provenance fields immutable |
| **GDELT Official anti-doping authorities** — `gdelt-official` · Tier 1 §30 | Public reporting restricted to `wada-ama.org`, `ita.sport`, `nadaindia.org`, `ndtl.nic.in` domains | `gdelt` (domain-restricted query) | Only pages GDELT has indexed and surfaced; official pages limited domain filter; not official records | Same as above; authority `OFFICIAL` | Same as above |
| **WADA News (official RSS)** — `wada-news-rss` · Tier 1 §35 | WADA public news feed (Prohibited List, Code/standards updates, news) | `rss` (generic feedparser connector) | WADA feed availability/latency; only featured publications | `canonical_url`, publisher (feed title), `published_at`, `retrieved_at`, content hash, authority `OFFICIAL` | Same as above |
| **WADA News & Releases (official page)** — `wada-news-releases` · Tier 1 §35 | WADA media/news release page | `web_doc` (HTML text extraction) | Page-structure changes can break extraction; text only, images not stored | `source_url`, `retrieved_at`, content hash, authority `OFFICIAL` | Same as above |
| **NADA India public notices** — `nadaindia-site` · Tier 1 §30/§32 | NADA India public site content | `web_doc` | **Disabled by default** until a stable public notices URL is confirmed by an operator; site structure may change; public material only | `source_url`, `retrieved_at`, content hash, authority `OFFICIAL` | Same as above |

## Architecture-only (not shipped) — §41–§45

| Source | Data | Connector | Limitations | Provenance | Retention |
|---|---|---|---|---|---|
| Common Crawl / Wayback | historical public web | — | no connector shipped; §41–§42 | n/a | once enabled: original_url + archive_url + archive_timestamp + retrieved_at must be stored |
| Public social media | permitted public content | — | §43 only (no auth bypass, no private accounts); no social connector shipped yet | platform, post ID, URL, account, publication/retrieval time, public status | store with §43-consistent controls |
| Commercial enrichment (OpenCorporates, Maltego, Talkwalker) | licensed company/source enrichment | — | §45; optional adapters only, never required | source provenance | per license |
| Dark web / Tor / markets | — | — | **Out of scope** (§44) | — | — |

## Register notes

1. **Source health**: each row carries live `health` (`ACTIVE | DEGRADED | FAILED |
   RATE_LIMITED | DISABLED`), `consecutive_failures` and last-success/last-failure times
   surfaced by `GET /osint/sources` and `/osint/sources/{id}/health` (§48).
2. **Rate limiting**: every configured source has `rate_limit_per_min`; the service
   enforces per-source windows and surfaces `RATE_LIMITED` health (§69).
3. **Authority classification** uses `OFFICIAL | PUBLIC_NEWS | PUBLIC_SOCIAL | ARCHIVAL
   | COMMERCIAL`; the UI shows origin, not credibility (§413, §249).
4. **Deduplication** (§51–§52): content-hash, canonical-URL and syndication dedupe keep
   `independent_sources` honest; a syndicated copy of one press release is never counted
   as independent corroboration.
5. **Legal disclaimer**: collection targets public/official material only; legal
   interpretation belongs to authorized professionals (§448), and source citations stay
   attached (§445).
6. Unknown or unauthorized private/laboratory/administered data is never claimed (§31,
   §34).

*Updated at gate 1006. The register grows only with operator-confirmed real sources.*