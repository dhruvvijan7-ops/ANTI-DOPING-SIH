# Architecture

**Last updated:** 2026-09-01

This document describes the CleanSport Intelligence architecture: components, how
they communicate, the data flow, the intelligence engine design, and how every alert
is explained. Sections that describe not-yet-implemented stages are explicitly marked
**DESIGNED (not implemented)** — see [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

---

## 1. System overview

```text
User
  ↓
Frontend  (planned, STAGE D)          React + TS + Vite + Tailwind/shadcn
  ↓  HTTPS/JSON
Backend API  (implemented, STAGE A)   FastAPI, /api/v1
  ↓
Business Logic  (implemented)         services (auth, audit); planned: intelligence,
                                      alerts, investigations, reporting, AI
  ↓
Intelligence/Analytics Engine         rules + ML + correlation + scoring
     (STAGE E — DESIGNED, not implemented)
  ↓
Database  (STAGE A/B)                 PostgreSQL 16, SQLAlchemy 2.x, Alembic
```

- **Frontend** authenticates, then calls the backend API. (Expected: React Flow for
  the relationship graph, Recharts for analytics, TanStack Query for data fetching.)
- **Backend API** enforces authentication (JWT) and server-validated RBAC
  (admin / investigator / intelligence analyst / viewer), then delegates to services.
- **Business logic** services own workflows (auth, audit today; intelligence,
  alerts, investigations, reporting, AI later).
- **Intelligence/Analytics Engine** converts stored intelligence + events into
  signals, correlations and priority scores (STAGE E).
- **Database** stores all entities; schema changes are versioned in migrations.

Roles and audit: sensitive actions are recorded in `audit_events`. JWT tokens carry
only a stable user id; roles are resolved from the database per request (D-009).

---

## 2. Data flow

```text
Data Sources (synthetic)                          STAGE D ingestion (planned)
  ↓
Data Ingestion   (sources, reports, provenance)   STAGE D
  ↓
Normalization     (categories, dates, dedupe)      STAGE D
  ↓
Entity Resolution (deterministic + fuzzy)          STAGE D
  ↓
Feature Generation (per-athlete time series)       STAGE E (DESIGNED)
  ↓
Rules + ML + Correlation (rule engine, Isolation Forest,
         temporal 45d, cross-source, network)      STAGE E (DESIGNED)
  ↓
Signal Generation (anomaly / rule / correlation)   STAGE E (DESIGNED)
  ↓
Priority Scoring  (composite, explainable)         STAGE E (DESIGNED)
  ↓
Alert                                             STAGE F (DESIGNED)
  ↓
Investigator triage (dismiss / monitor / escalate
         / request info / create case)             STAGE F/G (DESIGNED)
  ↓
Investigation (lines of enquiry, evidence, tasks,
        notes, findings, timeline, graph)          STAGE G (DESIGNED)
  ↓
Evidence / Findings (inculpatory/exculpatory/neutral)  STAGE G (DESIGNED)
  ↓
Report                                            STAGE I (DESIGNED)
```

Data enters at ingestion, processing happens in the analytics engine, and results
are stored in PostgreSQL (analysis runs, feature snapshots, anomaly/correlation/
network results, priority scores). Alerts are generated from that store; investigations
consume alerts and add evidence records.

---

## 3. Intelligence engine

**Status: DESIGNED for STAGE E; not yet implemented.** The design below is the
contract the engine will implement.

### 3.1 Rules

A deterministic, versioned rule engine (`rule_versions`, `rule_results`). Rules
encode domain heuristics (e.g. reporting patterns, event proximity, relationship
prevalence). Rule firings are recorded so every alert can state which rules triggered.

### 3.2 Anomaly detection

- **Method:** Isolation Forest (scikit-learn).
- **Why:** isolates unusual points in high-dimensional feature space without relying
  on a distributional assumption; well suited to mixed-signal feature vectors.
- **Features:** engineered per-athlete feature snapshots (temporal event density,
  source-mix, relationship counts, marker patterns), stored in `feature_snapshots`;
  model versions recorded in `model_versions`.
- **Anomaly score:** Isolation Forest score is normalized to a 0–100 signal where 50
  is the reference-population median; higher = more unusual *relative to the reference
  population* — explicitly not a probability of wrongdoing.
- **Explanation:** a per-feature contribution from the anomaly model so results state
  which features drove a signal.
- **Contribution:** the normalized anomaly signal feeds the composite priority score
  via its component weight.

### 3.3 Temporal analysis

Rolling-window correlation (`correlation_results`) over a configurable window
(default 45 days): clustering of events that are temporally proximate, and pattern
detection across an athlete's history (longitudinal view).

### 3.4 Network analysis

Entities and typed relationships from `entity_relationships` +
`relationship_types` (graph source of truth — D-003, no graph DB). Per-node metrics:
degree, weighted degree, connected alerts, relationship diversity. Association is
**not** evidence of wrongdoing — a documented analytical constraint.

### 3.5 Multi-source correlation

Signals from different categories (testing, reports, travel, medical, network) are
combined into compatible clusters; result records preserve which sources contributed.
Source diversity is treated as corroboration potential, not proof.

### 3.6 Priority scoring

**Status: DESIGNED (STAGE E).** The specified composite formula
(`00_MASTER_SPECIFICATION.md` §24) is:

```text
P = 0.25·R + 0.20·A + 0.20·C + 0.15·T + 0.10·N + 0.10·S
```

where R = rule signal, A = anomaly signal, C = cross-source correlation signal,
T = temporal signal, N = network signal, S = source-reliability/assessment signal,
each normalized 0–100. `P` is mapped to LOW / MODERATE / HIGH / VERY HIGH / CRITICAL.
Results include a decomposition showing each component's contribution.

> This formula is **not yet implemented**; the document will be updated in STAGE E
> when the actual implementation is verified, so the docs always match the code.

---

## 4. Explainability

Every alert must answer, for the analyst:

- **Why was this alert generated?** → alert + linked `alert_signals`.
- **Which signals contributed?** → `alert_signals` rows (rule / anomaly / correlation / network).
- **Which data sources contributed?** → source provenance from `intelligence_reports` → `intelligence_sources`; event records.
- **Which rules triggered?** → `rule_results` → `rule_versions`.
- **What anomaly was detected?** → `anomaly_results` snapshot + feature-level explanation.
- **What relationships were relevant?** → `network_results` + `entity_relationships`.
- **How was the priority calculated?** → `priority_scores` decomposition (component weights × scores).

Design requirement: an alert with no explanation path is a defect. This contract will
be verified in STAGE F tests.

---

## 5. AI assistant (STAGE H — DESIGNED)

- Retrieval-grounded: input restricted to records supplied for the current case; no
  other data.
- Output categorized: "Known from records" / "Analytical inference" / "Suggested
  investigation question".
- Deterministic fallback when no LLM key is configured (D-005). Never fabricates;
  never accuses. Human-in-the-loop.