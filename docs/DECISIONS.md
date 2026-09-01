# Decision Log

Records implementation decisions that deviate from, clarify or resolve conflicts in the
specification. Each entry: decision, reason, alternatives, consequences.

---

## D-001 — Merge of overlapping domain schemas (directive §12 vs research `03_DATABASE_SCHEMA.md`)

**Decision:** Treat the master engineering directive (§12) as authoritative where it
differs from the research database schema, and merge complementary fields into a single
coherent schema. The merged schema will use the directive's more explicit table names
(`evidence_items`, `evidence_links`, `evidence_metadata`, `entity_relationships`,
`relationship_types`, `investigation_findings`, `investigation_assignments`,
`alert_signals`, `source_assessments`, `intelligence_tags`, `priority_scores`,
`correlation_results`, `network_results`, `providers`, `supplement_events`,
`case_outcomes`, `report_versions`) while adopting the research schema's field-level
detail and index guidance for shared tables (`users`, `roles`, `permissions`,
`intelligence_reports`, `tests`/`testing_events`, `investigations`, `evidence`, etc.).

**Reason:** The two documents describe the same domain with different naming granularity.
The directive is the operative engineering source of truth and explicitly enumerates
first-class evidence sub-entities, alert signals, findings and assignments that are
required to satisfy the §29 evidence model, §25 alert model and §27 investigation model.

**Alternatives considered:**
- Use only the research `03_DATABASE_SCHEMA.md` as-is (single `evidence`, single
  `relationships`). Rejected: would not fully support evidence links/metadata,
  relationship types, alert signals or findings.
- Use only the directive §12. Rejected: would lose field-level detail and index guidance.

**Consequences:** The data dictionary (`docs/DATA_DICTIONARY.md`) documents the merged
schema. All references in `TRACEABILITY.md` use the merged table names. `component`
(generic subject link) columns such as `subject_type`/`subject_id` are used where a
record can link to any entity type (intelligence, alerts, indicators, relationships).

---

## D-002 — Primary navigation set (directive §38 vs UI research `08_UI_UX_SPEC.md`)

**Decision:** Use the directive §38 primary navigation as authoritative:
Dashboard, Intelligence (Inbox, Sources), Alerts, Athletes, Investigations (Active,
Closed), Reports, Analytics, Administration.

**Reason:** The directive is the operative master document and prohibits
"unnecessary navigation sections." The research UI doc additionally lists Graph and
Resources; these are valuable but not core to the demo workflow.

**Alternatives considered:**
- Add a top-level Graph and Resources section per the UI doc. Deferred.

**Consequences:** The relationship graph is embedded within the investigation workspace
(§28/§32) and the athlete profile (§40) where it is most useful, rather than a separate
top-level page. Analytics is exposed as a top-level section (execution history +
evaluation page). Resources is deferred to P1 and may be added under a section later
without structural change.

---

## D-003 — No separate graph database; graph views from relational joins

**Decision:** Represent relationships relationally in PostgreSQL and build graph views /
React Flow data from SQL joins (directive §9).

**Reason:** The specification explicitly forbids introducing a graph database for the
prototype and requires modularity that permits swapping it later.

**Alternatives considered:** Neo4j / similar. Rejected by directive §9.

**Consequences:** `entity_relationships` + `relationship_types` serve as the graph source
of truth. Network scoring and `/graph` endpoints query these tables.

---

## D-004 — Priority score, alert and outcome vocabulary kept strictly investigative

**Decision:** Every analytical output uses terms such as "investigative priority,"
"signal," "anomaly relative to reference population," "lead," and "prioritized review."
Never "guilt probability," "doping score," "conviction score," or "AI detected a doper."
Case outcomes never include an automatic "violation confirmed" option.

**Reason:** Mandated by directive §3, §13, §24 and the research security/privacy and
UI-UX docs. This is the core domain boundary.

**Alternatives considered:** none (non-negotiable).

**Consequences:** Enforced in database field names, API names, UI copy, chart labels, AI
prompts and report templates. ML output is labelled "feature profile unusual relative to
the reference population," not a suspicion verdict.

---

## D-005 — AI Assistant with deterministic fallback; retrieval-grounded only

**Decision:** The AI assistant operates strictly on retrieved case data, categorizes
output into "Known from records / Analytical inference / Suggested investigation
question," and falls back to a deterministic summarizer when no LLM key is configured.
The app remains fully usable without an external LLM.

**Reason:** Directive §33 and security/PRD require human-in-the-loop, no hallucination,
and no hard dependency on an external model.

**Alternatives considered:** requiring an LLM key. Rejected.

**Consequences:** `app/ai/` has a provider abstraction with a fallback implementation.
Facts are only drawn from records passed into the prompt; the fallback produces the same
grounded summaries without a model.

---

## D-006 — Prototype scope excludes production/real data and cross-organization infra

**Decision:** Synthetic data only. No real personal/medical/financial/confidential-source
data. No production anonymous-communication infrastructure, no cross-NADO sharing, no
scale-out infra.

**Reason:** Directive §14, §19, `07_TESTING_AND_DATA.md`, `06_SECURITY_PRIVACY.md` §2, and
the out-of-scope list.

**Consequences:** Demo uses fictional athletes (e.g. ATH-1047). Any "intake" feature is
labelled a controlled prototype concept, not production anonymity.

---

## D-007 — Schema version compatibility: Python 3.14 available

**Decision:** Backend targets the FastAPI/Pydantic v2/SQLAlchemy 2.x stack and verifies
compatibility with the installed Python 3.14 during STAGE A scaffolding (before
dependency lock). If a library is incompatible with 3.14, pin a compatible interpreter in
the Docker backend image (e.g. python:3.12-slim) and document it here.

**Reason:** Local machine has Python 3.14.3; some native dependencies (bcrypt/passlib,
psycopg, scikit-learn wheels) may lag. Docker image controls the runtime precisely.

**Alternatives considered:** forced single interpreter. Rejected to preserve both local
dev speed and reproducible Docker.

**Consequences:** `pyproject.toml`/`requirements.txt` plus Docker pin the interpreter; a
verified-down revision is recorded here if needed.

---

## D-008 — Reporting: content completeness over elaborate document formatting

**Decision:** Report generation focuses on a structured, complete, previewable document.
PDF/export is a best-effort enhancement layered on the same content model.

**Reason:** Directive §34 states report content generation is more important than
elaborate formatting, and export is "where feasible."

**Alternatives considered:** heavy PDF rendering pipeline. Deferred.

**Consequences:** `investigation_reports` + `report_versions` store structured content; a
preview renders sections; export (server-side) is added if time permits in STAGE I.

---

## D-009 — Authentication tokens with server-validated role/permissions

**Decision:** JWT access tokens carry a stable user identifier; user roles and permissions
are resolved server-side from the database on each request via the RBAC dependency. The
client never supplies role claims.

**Reason:** Directive §36/§60 and `06_SECURITY_PRIVACY.md` require backend authorization
and no trust in client-supplied roles.

**Alternatives considered:** putting roles in the JWT claims. Rejected: roles can change
and client-visible claims invite tampering/complexity.

**Consequences:** Current-user `/me`, role denials (403), and audit `actor` resolution all
rely on the server-side role lookup.

---

## D-010 — Admiralty scale source/information assessment model

**Decision:** Adopt WADA's two-axis Admiralty Scale for intelligence assessment:
source reliability A–F (source rating) and information accuracy 1–6 (information
rating), stored as a combined two-character notation (e.g. `A1`). Enforce constrained
enums on `intelligence_sources.reliability_default`,
`intelligence_reports.reliability`/`information_quality`, and
`source_assessments.reliability`/`information_quality` (STAGE B migration), plus a
six-level confidence lexicon (`CONFIRMED` … `VERY_UNLIKELY`) on analytic result
entities (STAGE E).

**Reason:** `docs/DOMAIN_VALIDATION.md` (concepts 3/4/5) confirmed WADA's official
methodology (IG Guidelines §5.1, §6.5; ISTI 11.3.1). The current free-string fields
do not enforce the two-axis model.

**Alternatives considered:** single free-text assessment. Rejected — would not encode
the WADA source/information distinction that investigations rely on.

**Consequences:** Admiralty enums applied in the STAGE B migration; taxonomy
crystalized in the data dictionary to a single canonical table (source rating range
varies A–F consistently; information rating range differs 1–5 vs 1–6 across editions —
use 1–6, the Apr 2021 guidelines range).

---

## D-011 — Every investigation finding is direction-labelled (inculpatory/exculpatory/neutral)

**Decision:** Add `evidential_direction` (`INCULPATORY`/`EXCULPATORY`/`NEUTRAL`) to
`investigation_findings`. Case outcomes must be able to reflect exculpatory material
(e.g. Closed — unsubstantiated after exculpatory evidence). This is a direct
enforcement of ISII 5.2/5.3.3 (purpose to prove *or disprove*; open mind), not a
softening of the product boundary.

**Reason:** `docs/DOMAIN_VALIDATION.md` concept 11. The master directive §4/§13
already requires non-guilty vocabulary; the finding schema must support the
exculpatory half of an investigation's purpose.

**Alternatives considered:** leaving findings undirected. Rejected — an investigator
cannot document an open-minded outcome without representing exculpatory evidence.

**Consequences:** `app/investigations/findings.py` (STAGE G) implements the flag; the
outcome set (D-004) links to it; AI/report language treats exculpatory findings as
first-class.

---

## D-012 — First-class "line of enquiry" entity in investigations

**Decision:** Add `investigation_lines_of_enquiry` (title, status, linked evidence,
owner, created/updated timestamps) to the investigation workspace, mirroring Jade ICM
and ISII 5.3.7 ("develop material into further lines of enquiry"). Lines of enquiry
are the unit of investigative work, distinct from tasks and notes.

**Reason:** `docs/DOMAIN_VALIDATION.md` concept 12 identified a gap versus the
authoritative framework and the Jade ICM design lesson in `05_COMPETITIVE_RESEARCH.md`.

**Alternatives considered:** modelling lines of enquiry as a task kind. Rejected —
tasks are actionable to-dos; lines of enquiry are avenues that produce evidence and
are linked to the evidence gathered.

**Consequences:** New table + workspace UI section in STAGE G; timeline/graph views
surface lines of enquiry; report template includes them.

---

*Decision log is extended as implementation proceeds.*
