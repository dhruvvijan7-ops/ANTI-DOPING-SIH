# Domain Validation — Anti-Doping Intelligence & Investigation Concepts

**Status:** Working draft (research pass 1)
**Last updated:** 2026-09-01
**Scope:** Validate the 20 core intelligence/investigation domain concepts behind
CleanSport Intelligence against authoritative anti-doping sources (WADA, ITA, NADA
India), record the real-world mechanism, map each to a proposed software
representation in this codebase, confirm implementation status, and flag required
modifications.

> **Product boundary (non-negotiable).** This document describes *investigative
> signals*, not findings of doping. Nothing here supports a "guilt probability",
> "doping score", or automatic "violation confirmed" outcome. Every mapping below
> preserves the `DATA → ANALYSIS → SIGNAL → PRIORITIZATION → HUMAN REVIEW → … →
> AUTHORIZED DECISION` pipeline mandated by the master directive (§3, §13, §24) and
> decision D-004.

---

## 1. Method

1. **Framework documents:** WADA 2027 *International Standard for Intelligence and
   Investigations* (ISII, final draft, in force 1 Jan 2027, adopted Busan 2025-12-05;
   drafting drafts consulted), WADA 2026 *International Standard for Testing and
   Investigations* (ISTI, effective 1 Apr 2026), WADA *Information Gathering and
   Intelligence Sharing Guidelines* (V1.0 Oct 2015 and Apr 2021 update), WADA 2027
   *World Anti-Doping Code*.
2. **Operational sources:** ITA REVEAL reporting platform and ITA I&I service pages,
   WADA Speak Up!, NADA India.
3. **Mapping basis:** master directive `00_MASTER_SPECIFICATION.md` (11-stage pipeline,
   §12 DB schema, §25 alerts, §27 investigations, §29 evidence, §4 outcomes) and the
   implemented STAGE B models (`backend/app/models/*`).
4. **Caveat on 2027 material:** The 2027 ISII is treated as the operative *future*
   framework (in force 1 Jan 2027). Where a concept is cited only from ISII, the
   current binding analogue in the 2021 ISTI is noted.

**Documents consulted (verbatim excerpts):**

| Ref | Document | Version / date | Source URL |
|---|---|---|---|
| [ISII] | International Standard for Intelligence and Investigations | 2027 final draft, effective 2027-01-01 | wada-ama.org (2026-03 PDF); final copy at itf-tkd.org (2025-12) |
| [ISII-SOC] | Summary of Major Changes — ISII Final Draft | 2025-10-31 | wada-ama.org |
| [ISII-2D] | ISII Second Draft + Summary | 2025-02 | wada-ama.org |
| [ISTI] | International Standard for Testing and Investigations | effective 2026-04-01 | wada-ama.org `isti_2026_eng.pdf` |
| [IG-GL] | Information Gathering and Intelligence Sharing Guidelines | V1.0 Oct 2015 (and Apr 2021 update) | wada-ama.org |
| [CODE] | World Anti-Doping Code | 2027 | wada-ama.org |
| [REVEAL] | ITA REVEAL platform / I&I service pages | accessed 2026 | ita.sport/service/reveal, ita.sport/athlete-hub/intelligence-investigations |

---

## 2. The 20 domain concepts

The validation scope is the canonical set of anti-doping intelligence/investigation
concepts derived from the WADA/ISTI/ISII framework and mapped 1:1 onto the
specification's 11-stage pipeline.

| # | Concept | Authoritative source | Real-world mechanism | Proposed software representation | Implementation status | Modification needed |
|---|---|---|---|---|---|---|
| 1 | Intelligence lifecycle / cycle (direction → collection → collation → evaluation → analysis → dissemination → review) | [IG-GL] §1.2 (successive steps); UK COP intelligence cycle (adapted) | Information is collected, collated into a retrievable store, evaluated for reliability/validity/relevance, analysed into intelligence, and disseminated to decision-makers who review requirements. | `intelligence_reports` status machine (`NEW → ASSESSED → CORRELATED → …`); `analysis_runs`; intelligence inbox; assessment-to-action workflow. | PARTIAL — capture/assess exists; explicit lifecycle status transitions not yet enforced. | Add lifecycle state to `intelligence_reports.status` (dedicated enum) and enforce on ingestion/assessment. |
| 2 | Raw Information vs Anti-Doping Intelligence (products of evaluation/analysis) | [ISII] def (Article 3); [IG-GL] §2 | Raw Information is unprocessed material; Anti-Doping Intelligence is the *product* of evaluating/analysing Raw Information for a user. Raw data must not be mistaken for finished intelligence. | Keep `intelligence_reports` (raw holdings) distinct from analytic output tables (`anomaly_results`, `correlation_results`, `network_results`, `priority_scores`, `intelligence_products`). | PARTIAL — tables are distinct; a first-class "intelligence product" entity is missing. | Add `intelligence_products` table (products: Intelligence Brief / Intelligence Assessment) in STAGE D. |
| 3 | Source reliability assessment — Admiralty Scale (source rating A–F) | [IG-GL] §5.1 (Admiralty Scale); [ISTI] 11.3.1 | Reliability of the *source* is assessed separately from accuracy of the *information*: A Completely Reliable → F Reliability Unknown (basis: history, motivation, access). | `intelligence_sources.reliability_default`; `source_assessments.reliability`. | PARTIAL — single free string per record; two-axis Admiralty coding not enforced. | Enforce source axis A–F as constrained enum; store as part of an `admiralty_code` (e.g. `A1`). |
| 4 | Information accuracy assessment — Admiralty Scale (information rating 1–6) | [IG-GL] §5.1 | Accuracy of the *item of information* is rated 1 Confirmed → 6 Cannot be evaluated (corroboration by independent sources). | `intelligence_reports.information_quality`; `source_assessments.information_quality`. | PARTIAL — stored but not constrained to 1–6. | Constrain info axis 1–6 as enum; require the combined two-character notation. |
| 5 | Confidence levels for analytic assessments | [IG-GL] §6.5 | Analytic conclusions are labelled: Confirmed (100%, requires ≥2 independent sources), Probable (80–99%), Likely (60–79%), Possible (40–59%), Unlikely (20–39%), Very Unlikely (<20%). | `alert_signals`/`anomaly_results`/`correlation_results` confidence or `source_assessments` confidence. | NOT_STARTED — no confidence-level field in analytics results. | Add `confidence` field with the six-level lexicon to analytic result entities; never present as a probability of guilt. |
| 6 | Comprehensive intelligence capture / receipt from all sources | [ISTI] 11.2, 11.3.1; [ISII] 4.1; [REVEAL] | ADOs ensure they can obtain, assess and process intelligence from all available sources (reporting forms, hotlines, OSINT, partner ADOs, law-enforcement-derived leads). | `intelligence_sources.source_type` + ingestion contract (`app/intelligence/ingestion.py`); intake UI labelled prototype (D-006). | PARTIAL — model exists; intake UI/API not yet built (STAGE D). | No structural change; enforce a "source type taxonomy" during ingestion (STAGE D). |
| 7 | Intelligence assessment & analysis (relevance, reliability, accuracy; patterns/trends) | [ISTI] 11.3.1, 11.3.2; [IG-GL] §3 | Every item is assessed on receipt for relevance, reliability and accuracy; deeper analysis establishes patterns, trends and relationships. | `source_assessments`; `app/analysis/` (features, correlation, network). | PARTIAL — assessment model exists; analysis pipeline in STAGE E. | Persist per-item assessment of *relevance* (currently only reliability + quality). |
| 8 | Intelligence-led test planning (TDP) & target testing | [ISTI] 11.4; [ISII] 4.3.2 comment; ADNO study (intel-led planning associated with more ADRVs) | Intelligence informs effective, intelligent, proportionate Test Distribution Plans and Target Testing. | Analytic output consumed by testing-plan features; `testing_events`; target-testing recommendations. | MODEL EXISTS — `testing_events`, `biological_observations` present; target-testing planner not built. | Add a "target testing recommendation" entity surfaced from `priority_scores` (STAGE E). |
| 9 | Intelligence products — Intelligence Brief & Intelligence Assessment | [IG-GL] §7.3 | Operational (Brief: summary/background/analysis/conclusion) and Strategic (Assessment: exec summary/issue/background/discussion/conclusion/recommendations) report formats. | `intelligence_products` (new) and/or `investigation_reports` + `report_versions`. | NOT_STARTED | Add product-kind taxonomy: `OPERATIONAL_BRIEF`, `STRATEGIC_ASSESSMENT` (STAGE I). |
| 10 | Investigation initiation threshold — reasonable cause | [ISII] 5.3.1 (+ comment); [ISII-SOC] | Investigations are initiated on *reasonable cause to believe* a breach may have occurred — credible information, not mere speculation/hunch. Protects against arbitrary investigation. | Alert-to-case conversion with mandatory "basis of initiation" rationale field; case creation records the supporting signal(s). | DESIGNED — alert triage (§26) and convert-to-case in spec; investigation model pending (STAGE G). | Add required `initiation_basis`/`reasonable_cause` note on case creation (STAGE G). |
| 11 | Purpose of investigation — prove or disprove; open mind; exculpatory & inculpatory | [ISII] 5.2, 5.3.3; [10_RESEARCH] | Investigations are conducted impartially, objectively, with an open mind; the purpose includes gathering sufficient evidence to prove *or disprove* a violation — i.e. both inculpatory and exculpatory material. | `investigation_findings` with an evidentiary-direction flag; allowed case outcomes include exculpatory grounds (D-004). | DESIGNED — findings/outcomes model planned (STAGE G). | Add `evidential_direction` (`INCULPATORY`/`EXCULPATORY`/`NEUTRAL`) to `investigation_findings`; ensure outcome set supports it. **HIGH PRIORITY.** |
| 12 | Lines of enquiry | [ISII] 5.3.7; [IG-GL]; Jade ICM parallels | Evidence is gathered to develop *further lines of enquiry* and reliable evidence; investigation plans identify avenues of enquiry. | Investigation workspace should expose explicit "lines of enquiry" as first-class case records (parallel to Jade ICM). | NOT_STARTED — not in current schema. | Add `investigation_lines_of_enquiry` entity (title, status open/ongoing/exhausted, linked evidence) in STAGE G. **HIGH PRIORITY.** |
| 13 | Investigation plan, resources & powers | [ISII] 5.3.2, 5.3.5 | Each investigation is planned; investigators are qualified/experienced; ADOs use all available investigative resources and powers (documents, data, partner cooperation). | Case workspace: investigation plan entity, assignment (qualifications), evidence/tasks supporting the plan. | PARTIAL — `investigation_assignments`, `investigation_tasks` in spec; model pending. | Add optional `plan` (objectives + avenues) to `investigations` (STAGE G). |
| 14 | Confidential handling — need-to-know | [ISII] 5.3.8 (+ comment); [IG-GL] | Intelligence/evidence is treated confidentially and shared only where appropriate, on a need-to-know basis, per the data-protection standard and applicable law. | `confidentiality` on sources/reports; RBAC (4 roles); audit trail; access logging on sensitive routes. | PARTIAL — confidentiality fields + RBAC exist; no per-record access policy. | Optional: per-record read-permission/need-to-know tag; keep RBAC as the baseline (STAGE D). |
| 15 | Documentation of conduct, evidence and outcome | [ISII] 5.3.9 | ADOs document the conduct of an investigation (statements/interviews, record of enquiries), the evidence identified, and the outcome. | `investigation_notes` (immutable, audited), `investigation_actions`, `evidence_items`, `case_outcomes`, `investigation_reports`. | DESIGNED — models planned (STAGE G). | No structural change beyond #11/#12; enforce immutable audit trail. |
| 16 | Source protection & confidential reporting | [ISII] 2.5; [REVEAL]; [Speak Up] | Reporters/Confidential Human Sources are protected; reporting platforms allow anonymous/confidential intake; protection of identity is paramount. Prototype explicitly does not claim production anonymity (D-006). | Intake UI (anonymous toggle, confidentiality) labelled "controlled prototype concept"; `confidentiality` field; source protection in source-handling. | DESIGNED — intake is STAGE D; D-006 caps claims. | No structural change; add source-protection notice in intake copy (STAGE D). |
| 17 | Longitudinal intelligence / biological profiling (ABP-style time-series) | [ISTI] ABP framework; ITA "Sample Testing / ABP" | Repeated measurements over time (biological markers, whereabouts patterns) build a longitudinal profile; deviations relative to the athlete's own history are signals. | `biological_observations`, `whereabouts_events`; temporal correlation (45d window) and feature snapshots over the profile. | MODEL EXISTS — events tables present; longitudinal feature pipeline in STAGE E. | No structural change; ensure time-series features are computed per-athlete in STAGE E. |
| 18 | Athlete Support Personnel (ASP) investigations | [ISII] 5.3.4 (minors/protected persons); [CODE] 2.5/2.7/2.8/2.9/2.10; [REVEAL] ("ADRVs beyond testing, incl. ASP") | Non-analytical ADRVs (Administration, Complicity, Trafficking, Tampering, Prohibited Association) involve ASP; investigations and reporting channels cover them. | `support_person` entity; `entity_relationships` typed to ADRV-relevant associations; alerts/cases can target support persons. | PARTIAL — `support_person` exists; relationship types are generic. | Seed ADRV-aware `relationship_types` (e.g. `supply_relationship`, `administration_connection`, `complicity_association`) and allow cases predicated on non-analytical ADRVs (STAGE C seed + STAGE G). **HIGH PRIORITY.** |
| 19 | Cross-organization intelligence sharing & collaboration | [ISII] 4.2/5.3.8 need-to-know; WADA SISP/GAIIN; [REVEAL] network | ADOs share intelligence with each other, WADA, law enforcement on a justified basis; SISP/GAIIN institutionalize exchange. Prototype does not implement production sharing (D-006). | Documented as future capability; sharing agreements / partner orgs intentionally out of scope. | NOT_STARTED (out of scope per D-006) | None for prototype; capture as P1 note in DECISIONS/architecture. |
| 20 | Investigation outcomes — documented, human-authorized | [ISII] 5.3.9; [IG-GL] §7; directive §4 | Outcomes are documented and decided by humans; prototype allowed outcomes: Closed no action, Closed false positive, Unsubstantiated, Escalated, Referred, Further monitoring. Never automatic "doping violation confirmed". | `case_outcomes` constrained enum (D-004); outcome selection human-only. | DESIGNED — `case_outcomes` enumerated in spec/TRACEABILITY; model pending. | No change; enforces non-guilty vocabulary. Outcome must reference #11 direction. |

---

## 3. Findings summary

### 3.1 Domain concepts that validate the current design as-is (no change)

- **Concept 6 (all-sources capture), 14 (need-to-know/RBAC), 16 (source protection
  claims), 17 (longitudinal/ABP-style), 20 (human-authorized outcomes)** — the
  specification's models, RBAC, D-004/D-006 decisions, and `events` tables already
  align with WADA/ISTI/ISII requirements. No structural change.

### 3.2 Gaps that require modification (design-time debts)

| # | Gap | Required change | Owner stage |
|---|---|---|---|
| 11 | Exculpatory evidence not representable explicitly | `investigation_findings.evidential_direction` enum + outcome support | STAGE G (model + tests) |
| 12 | No first-class "line of enquiry" entity | New `investigation_lines_of_enquiry` table + workspace UI | STAGE G |
| 3/4 | Admiralty two-axis (A–F / 1–6) not enforced | Constrained enums + `admiralty_code` (e.g. `A1`) on `source_assessments`/`intelligence_reports` | STAGE B migration (before apply) + STAGE D |
| 5 | Analytic confidence lexicon missing | `confidence` six-level field on analytic result entities | STAGE E |
| 18 | Relationship types not ADRV-aware | Seed ADRV-relevant `relationship_types`; allow non-analytical ADRV predicates | STAGE C seed + STAGE G |
| 2/9 | No "intelligence product" first-class entity | `intelligence_products` + product-kind taxonomy | STAGE D/I |

### 3.3 Terminology compliance (D-004)

All concepts above are mapped to investigative vocabulary; no mapping introduces a
guilt-probability or automatic-conviction construct. Concept 11 explicitly requires
*exculpatory* signal handling, which strengthens rather than weakens the product
boundary.

---

## 4. Source register (primary, with confidence grade)

| Source | Use | Grade |
|---|---|---|
| WADA — 2027 ISII final draft (`2026-03` PDF; itf-tkd copy 2025-12) | Concepts 2, 10, 11, 12, 13, 14, 15, 16, 19 | High (operative 2027 framework; draft text verified against two copies) |
| WADA — ISII Summary of Major Changes (final draft, 2025-10-31) | Reasonable-cause threshold (10), minors/protected persons (18), self-incrimination rights | High |
| WADA — ISII Second Draft + summary (2025-02) | Purpose of investigations (11), Admiralty-independent assessment model history | High |
| WADA — ISTI effective 1 Apr 2026 (`isti_2026_eng.pdf`) | ISTI 11.3.1/11.3.2 assessment (7), current binding standards | High |
| WADA — IG Guidelines Oct 2015 V1.0 / Apr 2021 | Admiralty Scale A–F & 1–6 (3, 4), confidence levels (5), intelligence products (9), lifecycle (1) | High (two versions corroborate) |
| WADA — 2027 Code | ADRV articles 2.5/2.7/2.8/2.9/2.10/2.11 (18) | High |
| ITA — REVEAL + I&I pages | Anonymous/confidential intake (6, 16), assess-triaction (7), ASP/non-analytical ADRVs (18), sharing network (19) | High |
| NADA India (ABP PDF; I&I workshops; GAIIN Delhi 2026) | Context, ABP (17), India-relevant NADO positioning | Medium (mostly context) |
| Anti-Doping Norway study (Drug Test. Anal. 2023;15) | Intelligence-led testing associated with more ADRVs (8) | Medium (supporting) |
| UK College of Policing APP (intelligence cycle) | Generic intelligence-cycle stages (1) — adapted, not a WADA source | Low (supplementary) |

**Read carefully:**
- WADA guidelines are *non-mandatory* third-level documents; the ISII (2027) and ISTI
  (2026) are the binding standards.
- 2027 ISII/Code are future frameworks (in force 1 Jan 2027). Current binding analogue
  for most concepts is the 2021/2026 ISTI; both point in the same direction for the
  concepts listed.
- Admiralty Scale letter/number codings vary slightly between editions (source A–F is
  consistent; information rating range 1–5/1–6). This document uses A–F and 1–6 and
  should be crystalized to a single canonical table in the data dictionary.

---

## 5. Follow-up actions

- [ ] STAGE B migration: add Admiralty enums + `admiralty_code` (gaps 3/4).
- [ ] STAGE C seed: ADRV-aware `relationship_types` (gap 18).
- [ ] STAGE D: `intelligence_products` + product-kind (gaps 2/9); lifecycle status enum (1); relevance on assessments (7); ingest source-type taxonomy (6).
- [ ] STAGE E: analytic confidence lexicon (5); target-testing recommendations from `priority_scores` (8); per-athlete longitudinal features (17).
- [ ] STAGE G: `investigation_lines_of_enquiry` (12); `evidential_direction` on findings + outcome linkage (11); `initiation_basis` (10); plan entity (13).
- [ ] STAGE I: product-kind + `intelligence_products` report rendering (9).
- [ ] Update `docs/TRACEABILITY.md`, `docs/DATA_DICTIONARY.md`, `docs/DECISIONS.md`
      (new decision entries for Admiralty model, line-of-enquiry, exculpatory-direction)
      as each gap is closed.

*Research pass 1 complete 2026-09-01. Re-run whenever a binding standard version changes (e.g., ISII final ratification or ISTI updates).*