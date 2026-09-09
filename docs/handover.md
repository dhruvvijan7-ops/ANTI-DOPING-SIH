# HANDOVER.md --- SIH1721 Anti-Doping Intelligence & Investigations Platform

**Project:** Intelligence & Investigations --- Enhancing Anti-Doping
Efforts\
**SIH Problem Statement:** SIH1721\
**Provider:** Ministry of Youth Affairs & Sports / Department of Sports
/ National Anti-Doping Agency (NADA)\
**Category:** Software\
**Theme:** Smart Automation\
**Status:** Post-prompt implementation handover / baseline for
repository verification

------------------------------------------------------------------------

# 1. Purpose of this handover

This is the master handover for everything established through the
project-planning and coding-agent prompt sequence. It is intended to let
a new developer or coding agent understand the product, domain,
architecture, intended implementation, prompt history, repository
decisions, intelligence logic, investigation workflow, security model,
testing expectations, and remaining verification work without needing
the original conversation.

**Important distinction:** this document records the implementation
specification and the expected state resulting from the prompts. The
actual Git repository is the source of truth for what the coding agent
physically implemented. Therefore, anything not verified from the
repository/runtime must be treated as "verify" rather than falsely
claimed as working.

------------------------------------------------------------------------

# 2. Project problem and objective

The project is based on SIH1721, **"Intelligence and Investigations -
Enhancing Anti-Doping Efforts."** The problem calls for a comprehensive
intelligence and investigation system for anti-doping work. The system
should bring together testing results, Athlete Biological Passport (ABP)
information, third-party intelligence and other relevant information,
apply analytics/AI to identify suspicious patterns and anomalies, and
convert those findings into actionable investigative intelligence.

The problem also calls for capabilities around:

-   centralized and secure data;
-   analytical tools and visualizations;
-   predictive/risk prioritization;
-   investigation and case tracking;
-   documentation;
-   evidence management;
-   investigator collaboration;
-   automated/assisted reporting;
-   confidential whistleblower/informant communication;
-   training/resource material.

The product therefore cannot be treated as merely an ML classifier or
dashboard.

The intended chain is:

``` text
Data
  ↓
Normalization
  ↓
Entity Resolution
  ↓
Intelligence Analysis
  ↓
Signals
  ↓
Correlation
  ↓
Explainable Priority Score
  ↓
Alert
  ↓
Human Investigator Review
  ↓
Investigation
  ↓
Evidence / Notes / Tasks / Findings
  ↓
AI-Assisted Synthesis
  ↓
Report
  ↓
Audit Trail
```

------------------------------------------------------------------------

# 3. Product definition

## 3.1 One-line definition

A secure anti-doping intelligence platform that correlates multi-source
information, detects unusual patterns, prioritizes investigative leads,
explains why they were flagged, and gives investigators a structured
workspace to investigate and document those leads.

## 3.2 Product metaphor

The simplest way to understand the product is:

> **A digital investigation room for anti-doping intelligence.**

It helps an investigator answer:

> **"Out of all the information we have, which situations deserve my
> attention, and why?"**

## 3.3 What it is NOT

It is not a system whose job is to automatically declare that an athlete
is doping or guilty.

It is not a replacement for every operational anti-doping system.

It is not a generic SOC, generic crime-management system, consumer
health application, or autonomous enforcement engine.

------------------------------------------------------------------------

# 4. Core product principles

1.  **Human in the loop:** automated analysis produces leads; authorized
    investigators make decisions.
2.  **Explainability:** every important signal/score must explain its
    contributing information.
3.  **Evidence orientation:** findings should be linked to underlying
    information.
4.  **Multi-source correlation:** meaningful intelligence can emerge
    only when different sources are connected.
5.  **Longitudinal analysis:** historical patterns matter.
6.  **Relationship analysis:** athlete/support-person/provider
    relationships can add context.
7.  **Auditability:** important actions and automated outputs must be
    traceable.
8.  **Privacy:** use synthetic data in the prototype and protect
    sensitive information by design.
9.  **Extensibility:** new sources and AI providers should be addable
    without rewriting the core system.
10. **Modular simplicity:** use a modular monolith rather than
    unnecessary distributed infrastructure.
11. **No unsupported accusations:** a score or anomaly is an
    investigative-priority signal, not proof of an ADRV.
12. **Prototype honesty:** never call mocked functionality
    production-ready.

------------------------------------------------------------------------

# 5. Critical terminology rules

The UI and AI assistant must prefer:

-   investigative lead;
-   suspicious indicator;
-   unusual pattern;
-   potential concern;
-   requires review;
-   investigation recommended;
-   corroborating intelligence;
-   high-priority alert;
-   monitoring.

Avoid:

-   guilty athlete;
-   confirmed doping;
-   doper;
-   AI proved violation;
-   automatic guilt;
-   automatic ADRV determination.

The following distinctions are fundamental:

``` text
Anomaly ≠ Evidence
Evidence ≠ Guilt
Priority score ≠ Probability of guilt
AI summary ≠ Investigator finding
Machine signal ≠ Regulatory determination
```

------------------------------------------------------------------------

# 6. Research baseline established

The research established that the real anti-doping ecosystem already
contains multiple specialized systems and organizations. The project
should therefore be positioned as an **intelligence-analysis and
investigation layer**, not as a claim that it replaces the whole
ecosystem.

Research covered:

-   NADA India;
-   WADA;
-   WADA ADAMS;
-   WADA Speak Up!;
-   ITA Intelligence & Investigations;
-   ITA REVEAL;
-   secure intelligence-sharing concepts such as SISP;
-   Jade ICM;
-   academic anti-doping AI prototypes including NADARAI;
-   WADA testing/investigation and ABP guidance.

The research conclusion was that the ecosystem is fragmented across
operational data, confidential reporting, investigation/case management,
and intelligence analysis. The proposed project combines the analysis
and investigation workflow into one prototype.

------------------------------------------------------------------------

# 7. Domain research conclusions

## 7.1 NADA India

NADA India has functions including Sample Collection, Results
Management, Education & Awareness, Science & Research, and Intelligence
& Investigations. Intelligence & Investigations concerns gathering
intelligence and carrying out investigations related to doping
misconduct.

NADA's privacy material also recognizes investigation information can
include open-source searches, witnesses/confidential sources,
law-enforcement cooperation, and other external stakeholders. This is
why confidentiality, access control and synthetic prototype data are
important.

## 7.2 WADA intelligence/investigation principles

The current operational baseline researched was the WADA International
Standard for Testing and Investigations. Important principles
established for the product are:

-   obtain, assess and process intelligence;
-   use many possible intelligence sources;
-   handle information securely and confidentially;
-   protect sources;
-   conduct evidence-driven investigations;
-   consider both inculpatory and exculpatory evidence;
-   do not equate an analytical anomaly with automatic proof of an
    anti-doping rule violation.

Future 2027 standalone ISII material was treated as design guidance
only, not as the current mandatory baseline.

## 7.3 ABP

The Athlete Biological Passport is longitudinal. The system should show
unusual longitudinal behavior as a signal requiring review. An atypical
passport finding must not be represented by the product as automatic
proof of wrongdoing.

## 7.4 ADAMS

ADAMS is an existing secure centralized anti-doping information system
containing areas such as whereabouts, testing history, laboratory
results, ABP and TUE-related information. The proposed product is
therefore better understood as an intelligence and
investigation-analysis layer around relevant data rather than a
replacement for ADAMS.

## 7.5 Confidential reporting

WADA Speak Up! and ITA REVEAL demonstrate that secure/confidential
reporting and source protection are real requirements in this domain.
The prototype can represent this flow using synthetic data, but must not
claim production-grade whistleblower protection unless independently
implemented and secured.

------------------------------------------------------------------------

# 8. Existing-product/competitor analysis

## ADAMS

Role: operational anti-doping information system.

Relevant lesson: the proposed product should focus on correlation,
prioritization, investigation workflow and analysis rather than
pretending centralized operational records do not already exist.

## Speak Up!

Role: confidential reporting.

Relevant lesson: confidentiality and source protection need to be
first-class concepts.

## ITA Intelligence & Investigations / REVEAL

Role: intelligence gathering, assessment, analysis, investigations,
source handling and confidential reporting.

Relevant lesson: the project's intelligence workflow is realistic and
domain-aligned.

## Jade ICM

Role: investigations/case management, evidence, lines of enquiry, tasks
and case workflows.

Relevant lesson: investigation management is a substantial product area
and validates the case-management side of the design.

## NADARAI academic prototype

A public academic prototype used React/FastAPI/SQLite/SQLAlchemy,
JWT/RBAC, synthetic athlete testing records, rules, Isolation Forest and
composite risk scoring.

The proposed implementation differentiates through:

-   multi-source correlation;
-   temporal correlation;
-   relationship/network analysis;
-   evidence-linked cases;
-   explainability;
-   investigation workflow;
-   audit trail;
-   grounded AI assistance;
-   stronger separation between machine signals and investigator
    findings.

------------------------------------------------------------------------

# 9. Target users

The primary user is an authorized anti-doping intelligence/investigation
professional.

Potential roles include:

-   Administrator;
-   Investigator;
-   Analyst;
-   Reviewer.

Exact role names can remain implementation-specific, but backend
authorization is mandatory.

The platform is designed around an investigator's workflow rather than a
public-facing consumer workflow.

------------------------------------------------------------------------

# 10. End-to-end user journey

``` text
Login
  ↓
Dashboard
  ↓
Alerts / Intelligence
  ↓
Open Alert
  ↓
Open Athlete / Entity
  ↓
Why Was This Flagged?
  ↓
Review Signals
  ↓
Review Timeline
  ↓
Review Relationship Graph
  ↓
Review Supporting Intelligence
  ↓
Investigator Decision
  ├── Dismiss
  ├── Keep Under Review / Monitor
  └── Create Investigation
          ↓
       Investigation Workspace
          ↓
       Evidence
       Notes
       Tasks
       Timeline
       Relationships
       Findings
          ↓
       AI-Assisted Review
          ↓
       Report Draft
          ↓
       Investigator Review
          ↓
       Close / Continue Monitoring
          ↓
       Audit Trail
```

The complete path is the core product demonstration.

------------------------------------------------------------------------

# 11. Main product modules

Expected product modules:

``` text
Authentication
Dashboard
Athletes / Entities
Testing
ABP / Longitudinal Data
Intelligence
Travel / Whereabouts
Relationships
Analysis
Alerts
Investigations
Evidence
Tasks
Notes
Findings
AI Assistant
Reports
Audit
Administration / Settings
```

Some may be nested rather than top-level pages.

------------------------------------------------------------------------

# 12. Inputs

## Athlete data

Possible fields:

-   athlete ID;
-   name;
-   sport;
-   discipline;
-   team;
-   status;
-   historical records;
-   associated entities.

## Testing data

Possible fields:

-   test ID;
-   athlete ID;
-   sample date;
-   test type;
-   result;
-   substance/category metadata;
-   laboratory information;
-   location;
-   collection metadata;
-   historical result;
-   result status.

## ABP information

Possible fields:

-   athlete;
-   observation date;
-   biomarker/measurement category;
-   measurement value;
-   longitudinal history;
-   deviation/anomaly metadata;
-   quality/review metadata.

## Intelligence reports

Possible fields:

-   report ID;
-   source type;
-   source reliability;
-   confidence;
-   received date;
-   report text/structured content;
-   sensitivity;
-   linked entities;
-   status.

## Travel / whereabouts

Possible fields:

-   athlete;
-   date/time;
-   expected location;
-   actual location;
-   travel event;
-   destination;
-   source;
-   mismatch indicator.

## Relationships

Potential entities:

-   athletes;
-   coaches;
-   doctors/medical personnel;
-   support personnel;
-   teams;
-   organizations;
-   providers;
-   training facilities;
-   locations;
-   events;
-   other athletes.

------------------------------------------------------------------------

# 13. Core outputs

The platform produces:

1.  Signals.
2.  Explainable priority scores.
3.  Alerts.
4.  Investigator decisions.
5.  Investigation cases.
6.  Evidence links.
7.  Notes.
8.  Tasks.
9.  Timeline events.
10. Findings.
11. Relationship/network context.
12. AI-assisted summaries.
13. Reports.
14. Audit events.

------------------------------------------------------------------------

# 14. Intelligence engine

The intelligence engine is the technical heart of the product.

## 14.1 Processing pipeline

``` text
Raw / Imported Data
        ↓
Validation
        ↓
Normalization
        ↓
Entity Resolution
        ↓
Feature Engineering
        ↓
 ┌──────┬──────────────┬───────────────┐
 ↓      ↓              ↓               ↓
Rules  ML         Temporal        Network
 ↓      ↓              ↓               ↓
 └──────┴──────────────┴───────────────┘
                 ↓
        Cross-Source Correlation
                 ↓
          Priority Calculation
                 ↓
            Explanation
                 ↓
               Signal
                 ↓
              Alert
```

## 14.2 Deterministic rules

Rules represent known, explicitly defined patterns. Examples:

-   repeated unusual patterns;
-   temporal relationship between testing and other events;
-   repeated independent intelligence;
-   relevant relationship combinations;
-   unusual combinations of records.

Rules must be versioned.

## 14.3 Isolation Forest

The selected prototype ML method is **Isolation Forest** from
scikit-learn.

It is intended to identify unusual multidimensional observations.

Potential features include:

-   historical test statistics;
-   frequency/count features;
-   temporal features;
-   deviations;
-   intelligence-report counts;
-   relationship counts;
-   travel/testing relationships;
-   other normalized behavioral features.

ML output becomes a signal, not a verdict.

## 14.4 Temporal correlation

The engine looks for events occurring in meaningful temporal proximity.

Example:

``` text
Intelligence report
       ↓
Travel event
       ↓
Testing event
       ↓
Unusual result/pattern
```

Temporal correlation can raise priority when supported by other
information.

## 14.5 Cross-source correlation

Example:

``` text
Testing anomaly
      +
Travel inconsistency
      +
Independent intelligence
      +
Relevant relationship
      ↓
Higher investigative priority
```

The UI should show this reasoning instead of only displaying a final
number.

## 14.6 Network analysis

The relationship graph can expose:

-   repeated shared entities;
-   clusters;
-   central entities;
-   shared providers;
-   shared support personnel;
-   unusual relationship patterns.

A relationship alone is not proof of misconduct.

------------------------------------------------------------------------

# 15. Priority/risk scoring model

The prototype scoring formula established was:

``` text
Priority Score =
    25% Deterministic Indicator Score
  + 20% Longitudinal / Pattern Anomaly
  + 20% Cross-Source Correlation
  + 15% Temporal Clustering
  + 10% Relationship / Network Signal
  + 10% Source Reliability / Quality
```

Each component is normalized to 0--100.

Classification:

``` text
0–29    LOW
30–49   MODERATE
50–69   HIGH
70–84   VERY HIGH
85–100  CRITICAL
```

These are **prototype investigative-prioritization thresholds**, not
official NADA/WADA thresholds and not probabilities of guilt.

------------------------------------------------------------------------

# 16. Score explainability and versioning

Every score should retain:

-   final score;
-   classification;
-   component scores;
-   contributing signals;
-   supporting record IDs;
-   rule version(s);
-   model name/version;
-   source-quality contribution;
-   timestamp;
-   investigator decision.

Historical scores should not silently change when models/rules are
changed.

Example metadata:

``` text
model:
  name: isolation_forest
  version: 1.0

rule_set:
  version: 1.0
```

------------------------------------------------------------------------

# 17. Alert model

An alert is created from one or more signals.

Conceptual structure:

``` text
Signal A: longitudinal anomaly
Signal B: temporal relationship
Signal C: source corroboration
Signal D: network relationship
              ↓
       Alert Generator
              ↓
       Priority Score
              ↓
             Alert
```

An alert should include:

-   alert ID;
-   title;
-   subject entity;
-   timestamp;
-   priority score;
-   classification;
-   signal types;
-   explanation;
-   supporting records;
-   status;
-   recommended investigative action;
-   model/rule versions.

Possible statuses:

-   new;
-   acknowledged;
-   investigating;
-   dismissed;
-   monitoring;
-   converted to case;
-   closed.

------------------------------------------------------------------------

# 18. Investigation model

An investigation is the structured workspace created from an alert or
another authorized intelligence lead.

It should contain:

-   case ID;
-   title;
-   description;
-   subject entity;
-   status;
-   priority;
-   assigned investigator;
-   collaborators;
-   creation date;
-   due date;
-   objectives;
-   evidence;
-   notes;
-   tasks;
-   findings;
-   timeline;
-   relationships;
-   reports;
-   audit history.

Possible lifecycle:

``` text
NEW
 ↓
TRIAGED
 ↓
OPEN
 ↓
UNDER REVIEW
 ↓
EVIDENCE COLLECTION
 ↓
FINDINGS REVIEW
 ↓
REPORT DRAFT
 ↓
CLOSED
```

Additional statuses such as dismissed, suspended, monitoring and
reopened may be used.

------------------------------------------------------------------------

# 19. Evidence management

Evidence should have metadata such as:

-   evidence ID;
-   title;
-   type;
-   description;
-   source;
-   acquisition date;
-   linked case;
-   linked entity;
-   sensitivity;
-   integrity metadata where supported;
-   created by;
-   timestamps;
-   status.

Important principle: evidence should be auditable. Significant edits
should preserve history rather than silently destroying the original
record.

Future production hardening should consider:

-   file validation;
-   file size limits;
-   malware scanning;
-   encryption;
-   hashes;
-   versioning;
-   access audit;
-   retention policies.

------------------------------------------------------------------------

# 20. Notes, tasks and findings

## Notes

Should include:

-   author;
-   timestamp;
-   case;
-   content;
-   visibility/access rules;
-   relevant links.

## Tasks

Should include:

-   task ID;
-   title;
-   description;
-   assignee;
-   due date;
-   priority;
-   status;
-   case;
-   completion timestamp.

Examples:

-   verify source;
-   request additional record;
-   review test history;
-   review travel record;
-   examine relationship;
-   interview source;
-   prepare report.

## Findings

Findings are investigator-created conclusions based on reviewed
information.

They must remain distinct from automated signals:

``` text
Machine signal
      ≠
Investigator finding
      ≠
Legal/regulatory determination
```

Findings should link to supporting evidence where possible.

------------------------------------------------------------------------

# 21. Timeline

The timeline combines events from different sources into one
chronological investigation view.

Example:

``` text
Jan 10 — Training event
Jan 12 — Travel event
Jan 14 — Intelligence report
Jan 15 — Test
Jan 16 — Result
Jan 20 — Relationship update
Jan 25 — New intelligence
Feb 02 — Alert generated
Feb 03 — Investigation opened
```

It should support filtering by date, source, event type, entity and
investigation.

------------------------------------------------------------------------

# 22. Relationship graph

React Flow is the intended frontend visualization technology.

Example:

``` text
             Doctor
               │
               │
Coach ───── Athlete ───── Team
               │
               │
          Training Site
               │
               │
           Provider
```

The graph should help investigators understand connections, clusters and
repeated shared entities.

It must not imply guilt simply because a relationship exists.

------------------------------------------------------------------------

# 23. "Why was this flagged?" requirement

This is a critical product feature.

An investigator should never receive a score with no explanation.

Example:

``` text
Priority: 78 / 100
Classification: VERY HIGH

Contributing factors:
+ Longitudinal anomaly
+ Temporally related intelligence
+ Travel/testing timing correlation
+ Relevant relationship network
+ High-quality supporting source

This is an investigative prioritization signal,
not a determination of an anti-doping rule violation.
```

The explanation should allow the investigator to trace the score back to
data.

------------------------------------------------------------------------

# 24. Synthetic data strategy

The prototype must use synthetic data.

Reasons:

-   real athlete data is sensitive;
-   real medical data is sensitive;
-   real confidential-source information is sensitive;
-   a student/prototype environment should not require access to
    production anti-doping information.

Synthetic data should be realistic enough to demonstrate the
intelligence engine.

Required scenarios include:

## Normal

Mostly normal history.

Expected result: low/no alerting.

## Isolated anomaly

One unusual observation.

Expected result: signal, potentially low/moderate priority.

## Correlated anomaly

Multiple signals occur together.

Expected result: higher priority.

## Temporal scenario

Events occur in a meaningful sequence.

Expected result: temporal signal.

## Network scenario

Entities share meaningful relationships.

Expected result: network signal.

## Multi-source scenario

Independent information sources corroborate a pattern.

Expected result: stronger cross-source signal.

------------------------------------------------------------------------

# 25. Synthetic data reproducibility

Synthetic generation should be deterministic where practical.

Use:

-   fixed random seeds;
-   documented schemas;
-   repeatable scripts;
-   scenario identifiers;
-   ground-truth labels for evaluation.

This allows the same synthetic dataset to be recreated for testing and
demonstrations.

------------------------------------------------------------------------

# 26. Machine-learning evaluation

Evaluation should use:

-   precision;
-   recall;
-   F1;
-   false-positive rate;
-   ranking quality;
-   explanation completeness.

Because the data is synthetic, the project must not claim real-world
anti-doping detection accuracy.

Do not state "the model detects doping with X% accuracy" based only on
synthetic data.

------------------------------------------------------------------------

# 27. AI assistant

The AI assistant is an investigator-support feature.

Supported use cases:

### Case summary

Summarize known case information.

### Timeline summary

Turn events into a readable chronology.

### Signal explanation

Explain already-generated signals using their source records.

### Missing information

Identify unanswered questions.

### Investigation questions

Suggest questions an investigator may want to examine.

### Report drafting

Draft a report using verified case information.

The investigator must review generated content.

------------------------------------------------------------------------

# 28. AI grounding requirements

The AI must be grounded in the case context.

It may use:

-   case data;
-   linked evidence;
-   linked intelligence;
-   system-generated signals;
-   explicitly supplied context.

If information is not available, it should say that there is
insufficient information.

It must not:

-   invent evidence;
-   invent witnesses;
-   invent events;
-   invent source reports;
-   fabricate citations;
-   convert uncertainty into certainty;
-   make a final guilt decision.

Untrusted source text must be treated as data, not instructions. This is
particularly important for prompt-injection resistance.

------------------------------------------------------------------------

# 29. Reporting

A report should be generated from verified case data.

Suggested structure:

``` text
Case Information
Subject
Investigator
Purpose / Scope
Background
Trigger / Initial Intelligence
Timeline
Relevant Signals
Evidence
Relationships
Investigative Actions
Findings
Unresolved Questions
Assessment
Recommendations
Attachments / Evidence References
Audit Metadata
```

Reports should support versioning where practical.

An AI-generated report draft is not automatically a final official
report.

------------------------------------------------------------------------

# 30. Technology stack

## Frontend

-   React 19
-   TypeScript
-   Vite
-   Tailwind CSS
-   shadcn/ui
-   React Router
-   TanStack Query
-   Zustand
-   React Hook Form
-   Zod
-   Lucide React
-   Recharts
-   React Flow
-   Framer Motion where useful

## Backend

-   Python
-   FastAPI
-   Pydantic
-   SQLAlchemy
-   Alembic

## Database

-   PostgreSQL

## ML/data

-   Pandas
-   NumPy
-   scikit-learn
-   Isolation Forest

## Testing

-   pytest
-   HTTPX
-   Vitest
-   React Testing Library
-   Playwright

## Deployment

-   Docker
-   Docker Compose

------------------------------------------------------------------------

# 31. Architecture decision: modular monolith

The prototype intentionally uses a **modular monolith**, not
microservices.

Reasons:

-   easier development;
-   easier debugging;
-   simpler deployment;
-   fewer infrastructure dependencies;
-   clear domain modules;
-   easy path to future service extraction.

The code must still maintain internal module boundaries.

------------------------------------------------------------------------

# 32. High-level architecture

``` text
                    ┌─────────────────────┐
                    │      Frontend       │
                    │ React + TypeScript  │
                    └──────────┬──────────┘
                               │ REST API
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │     API Layer       │
                    └──────────┬──────────┘
                               │
       ┌───────────────────────┼────────────────────────┐
       │                       │                        │
       ▼                       ▼                        ▼
 Authentication          Domain Services        Intelligence
 RBAC                     Investigations        Rules
 Authorization            Evidence              ML
 Audit                    Alerts                Temporal
                          Reports               Correlation
                                                 Network
                                                 Scoring
       │                       │                        │
       └───────────────────────┼────────────────────────┘
                               │
                               ▼
                       ┌───────────────┐
                       │  PostgreSQL   │
                       └───────────────┘

Synthetic sources:
Testing / ABP / Intelligence / Travel / Relationships / History
```

------------------------------------------------------------------------

# 33. Backend architecture

Recommended conceptual flow:

``` text
API Route
   ↓
Service
   ↓
Domain Logic
   ↓
Repository / Data Access
   ↓
PostgreSQL
```

Avoid putting all business logic directly inside FastAPI route handlers.

Suggested backend structure:

``` text
backend/
  app/
    api/
    core/
    models/
    schemas/
    services/
    repositories/
    intelligence/
    investigations/
    reports/
    audit/
    auth/
    main.py
  migrations/
  tests/
```

The actual repository may organize this differently as long as
responsibilities remain separated.

------------------------------------------------------------------------

# 34. Intelligence module architecture

Conceptually:

``` text
intelligence/
  ingestion/
  normalization/
  entity_resolution/
  rules/
  anomaly_detection/
  temporal_analysis/
  correlation/
  network_analysis/
  scoring/
  alerts/
  explainability/
```

This makes each analytical technique replaceable and testable.

------------------------------------------------------------------------

# 35. Frontend architecture

The frontend should be modular and API-ready.

Possible areas:

``` text
components/
pages/
layouts/
routes/
services/
hooks/
lib/
store/
types/
features/
```

The exact final folder structure depends on the implementation already
created.

Frontend services should isolate API access, for example:

``` text
services/
  auth
  athletes
  intelligence
  alerts
  investigations
  evidence
  reports
```

This avoids hardcoding backend assumptions throughout UI components.

------------------------------------------------------------------------

# 36. State management

Use:

-   TanStack Query for server state;
-   Zustand for genuinely client-owned global state;
-   local state for local UI behavior.

Do not place every API response into global Zustand state.

------------------------------------------------------------------------

# 37. Forms and validation

Use React Hook Form + Zod on the frontend.

Validate:

-   required fields;
-   dates;
-   IDs;
-   enum/status values;
-   evidence metadata;
-   user input.

The backend must independently validate all input.

------------------------------------------------------------------------

# 38. Frontend UX requirements

The interface should look and behave like a serious investigation
platform.

Priorities:

-   information hierarchy;
-   readable tables;
-   strong alert visibility;
-   understandable scores;
-   useful charts;
-   timeline visualization;
-   relationship graph;
-   evidence navigation;
-   case status visibility;
-   minimal decorative clutter.

Every data-heavy page should support:

-   loading state;
-   empty state;
-   error state;
-   populated state.

------------------------------------------------------------------------

# 39. Accessibility

The frontend should support:

-   keyboard navigation;
-   semantic controls;
-   visible focus states;
-   accessible labels;
-   sufficient contrast;
-   usable tables;
-   clear error messages;
-   responsive layouts.

------------------------------------------------------------------------

# 40. API groups

The intended API domains are:

``` text
/auth
/dashboard
/athletes
/intelligence
/analysis
/alerts
/investigations
/evidence
/relationships
/reports
/audit
```

Exact endpoint names may differ in the repository.

APIs should provide:

-   request validation;
-   response validation/typing;
-   authorization;
-   useful errors;
-   pagination where necessary;
-   filtering;
-   stable identifiers;
-   documentation.

------------------------------------------------------------------------

# 41. Database design

Primary database: PostgreSQL.

ORM: SQLAlchemy.

Migration tool: Alembic.

Core domain concepts expected in the schema include equivalents of:

``` text
users
roles
permissions

tenants

athletes
entities
teams
organizations
providers
support_personnel
relationships

tests
test_results
abp_records
whereabouts
travel_events

intelligence_reports
intelligence_sources

signals
signal_evidence
alerts

investigations
investigation_members
investigation_tasks
investigation_notes
investigation_findings

evidence
evidence_links

timeline_events

reports
report_versions

audit_logs
```

The exact final schema can differ based on normalization and
implementation decisions.

Use:

-   primary keys;
-   foreign keys;
-   indexes;
-   constraints;
-   timestamps;
-   meaningful status fields.

------------------------------------------------------------------------

# 42. Authentication and RBAC

Authentication should use a secure session or JWT architecture.

Password storage should use a secure password hashing method such as
Argon2id or bcrypt.

RBAC must be enforced on the backend.

Frontend route hiding is not sufficient security.

Possible roles:

``` text
ADMIN
INVESTIGATOR
ANALYST
REVIEWER
```

The exact names can differ.

------------------------------------------------------------------------

# 43. Audit logging

Important actions should produce audit records.

Examples:

-   login;
-   logout;
-   record creation;
-   record modification;
-   case creation;
-   case assignment;
-   evidence creation/upload;
-   evidence access where appropriate;
-   status changes;
-   investigator decisions;
-   report generation;
-   administrative changes.

Audit fields should include:

-   actor;
-   action;
-   target;
-   timestamp;
-   relevant metadata;
-   outcome.

Sensitive information should not be unnecessarily written into logs.

------------------------------------------------------------------------

# 44. Security requirements

Required principles:

-   authentication;
-   authorization;
-   least privilege;
-   RBAC;
-   server-side permission checks;
-   input validation;
-   secure API design;
-   audit logging;
-   secret management;
-   synthetic data for the prototype;
-   no credentials in Git;
-   controlled evidence access.

Future production security review should cover:

-   broken access control;
-   IDOR;
-   injection;
-   insecure uploads;
-   token leakage;
-   sensitive-data exposure;
-   audit tampering;
-   unauthorized evidence access;
-   AI prompt injection;
-   AI data leakage;
-   malicious intelligence content;
-   report manipulation.

------------------------------------------------------------------------

# 45. Confidential reporting architecture

Prototype concept:

``` text
Reporter
   ↓
Secure/Confidential Submission
   ↓
Intelligence Record
   ↓
Source Protection Metadata
   ↓
Assessment
   ↓
Correlation
   ↓
Potential Signal / Alert
```

The prototype should use synthetic reporters and synthetic intelligence.

Do not expose source identity unnecessarily.

Source reliability should be represented separately from source
identity.

Do not claim that a prototype form is equivalent to production-grade
whistleblower security.

------------------------------------------------------------------------

# 46. Multi-tenancy and extensibility

The broader architecture was designed with future multi-tenancy in mind.

Potential mechanisms:

-   tenant ID on records;
-   tenant-scoped queries;
-   authorization filters;
-   row-level security where appropriate.

The prototype can initially behave as a single-organization system while
preserving the architecture for future expansion.

The project follows the principle:

> **Open for extension, closed to unnecessary modification.**

Potential future source adapters:

``` text
ADAMS Adapter
OSINT Adapter
Laboratory Adapter
Federation Adapter
Law-Enforcement Adapter
Reporting Adapter
```

The prototype can simulate these sources internally.

------------------------------------------------------------------------

# 47. AI provider abstraction

The AI integration should ideally be behind a provider interface:

``` text
AI Service
    ↓
Provider Interface
    ├── Provider A
    ├── Provider B
    └── Local / Future Provider
```

Core application logic should not depend directly on one vendor's API
format.

------------------------------------------------------------------------

# 48. Repository decisions

The project was intended to use a manually created GitHub repository
with:

``` text
Visibility: Private
Template: None
Add README: OFF
Add .gitignore: OFF
License: MIT
```

The reasoning was that the coding agent should create the
project-specific README and .gitignore rather than relying on generic
GitHub-generated files.

The repository is private so the project can remain controlled while
under development.

------------------------------------------------------------------------

# 49. Repository-management prompt requirements

The repository-management prompt was deliberately scheduled **after
Stage B/C and Domain Validation**.

Its job was to establish a stable baseline without redesigning the
application.

It instructed the agent to:

-   inspect the existing project/Git state;
-   preserve working functionality;
-   organize the repository;
-   create/update README;
-   create project-specific .gitignore;
-   create .env.example;
-   create documentation areas;
-   establish tests/CI structure;
-   document setup and architecture;
-   protect secrets;
-   use meaningful commits;
-   review diffs before committing.

Critical instruction:

> **Do not redesign or restart the application. Treat the currently
> validated B/C + Domain Validation state as the baseline and preserve
> all working functionality.**

------------------------------------------------------------------------

# 50. Expected repository structure

The repository-management prompt proposed a professional structure
similar to:

``` text
/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── CONTRIBUTING.md
├── CHANGELOG.md
│
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── research/
│   ├── algorithms/
│   ├── api/
│   ├── database/
│   └── testing/
│
├── frontend/
├── backend/
├── ml/
│
├── data/
│   ├── synthetic/
│   └── schemas/
│
├── scripts/
├── tests/
├── docker/
│
└── .github/
    ├── workflows/
    ├── ISSUE_TEMPLATE/
    └── PULL_REQUEST_TEMPLATE.md
```

If the actual implementation uses a different layout, do not force a
rewrite merely to match this tree. Preserve the repository's valid
architecture.

------------------------------------------------------------------------

# 51. Prompt sequence and purpose

The coding-agent process was intentionally staged.

``` text
1. Master Implementation Prompt
        ↓
2. Stage A — Foundation
        ↓
3. Stage B/C — Domain Model + Synthetic Intelligence
        ↓
4. Domain Validation Prompt
        ↓
5. GitHub / Repository Management Prompt
        ↓
6. Stage D/E — Intelligence Engine
        ↓
7. Stage F/G — Alerts + Investigations
        ↓
8. Stage H/I — AI + Reporting
        ↓
9. Final Verification
```

The ordering is part of the handover.

------------------------------------------------------------------------

# 52. Master implementation prompt --- what it established

The master prompt defined the complete target system rather than just a
UI.

It established:

-   SIH1721 domain alignment;
-   product vision;
-   human-in-the-loop operation;
-   synthetic data;
-   modular-monolith architecture;
-   React/TypeScript frontend;
-   FastAPI/Python backend;
-   PostgreSQL;
-   SQLAlchemy/Alembic;
-   deterministic rules;
-   Isolation Forest;
-   temporal analysis;
-   cross-source correlation;
-   relationship analysis;
-   explainable scoring;
-   alerts;
-   investigations;
-   evidence;
-   notes/tasks/findings;
-   AI assistance;
-   reports;
-   audit;
-   security;
-   testing;
-   documentation.

Expected outcome: the agent understood the project as an end-to-end
platform.

------------------------------------------------------------------------

# 53. Stage A --- Foundation

Purpose: establish a maintainable technical foundation.

Expected work included:

-   frontend project setup;
-   backend project setup;
-   dependency installation;
-   TypeScript configuration;
-   Tailwind/shadcn configuration;
-   routing;
-   providers;
-   theme support;
-   query state;
-   client state;
-   reusable components;
-   API foundation;
-   environment configuration;
-   linting;
-   formatting;
-   type safety;
-   basic test infrastructure.

Expected result: a runnable project foundation that could support the
domain without a rewrite.

------------------------------------------------------------------------

# 54. Stage B/C --- Domain model + synthetic intelligence

Purpose: move from generic application scaffolding to the actual
anti-doping domain.

Expected work:

-   athlete entities;
-   testing data;
-   ABP-related records;
-   intelligence reports;
-   travel/whereabouts;
-   relationships;
-   database models;
-   migrations;
-   synthetic dataset;
-   basic signal concepts;
-   domain APIs;
-   domain-facing dashboard/profile functionality.

Expected result: a domain-aware application with actual internal data
structures and synthetic information.

------------------------------------------------------------------------

# 55. Domain validation prompt

Purpose: make sure the implementation actually solves the SIH1721
problem.

Validation areas:

-   anti-doping terminology;
-   entities;
-   data relationships;
-   intelligence sources;
-   ABP interpretation;
-   testing history;
-   travel/whereabouts;
-   alert semantics;
-   score semantics;
-   human review;
-   synthetic data;
-   privacy;
-   security.

The validation stage prevents drift into unrelated generic detection
software.

------------------------------------------------------------------------

# 56. GitHub/repository-management stage

Purpose: establish source-control and documentation discipline after a
validated domain baseline existed.

Expected output:

-   organized repository;
-   README;
-   license;
-   .gitignore;
-   .env.example;
-   documentation tree;
-   testing structure;
-   CI direction;
-   meaningful Git history;
-   project status documentation.

The agent was told not to restart/rewrite the existing implementation.

------------------------------------------------------------------------

# 57. Stage D/E --- Intelligence engine

Purpose: make the platform actually analyze information.

Expected implementation:

-   data preprocessing;
-   deterministic rules;
-   feature extraction;
-   Isolation Forest anomaly detection;
-   temporal analysis;
-   cross-source correlation;
-   network/relationship signals;
-   weighted priority scoring;
-   explanations;
-   signal persistence;
-   alert preparation.

The important output is not merely a model prediction. It is an
explainable investigative signal.

------------------------------------------------------------------------

# 58. Stage F/G --- Alerts + Investigations

Purpose: turn analytical output into investigator workflow.

Expected implementation:

-   alert list;
-   filters;
-   alert detail;
-   score explanation;
-   alert status transitions;
-   dismiss/monitor/investigate decisions;
-   alert-to-case conversion;
-   investigation list;
-   investigation detail;
-   assignment;
-   notes;
-   tasks;
-   evidence;
-   findings;
-   timeline;
-   relationships.

------------------------------------------------------------------------

# 59. Stage H/I --- AI + reporting

Purpose: complete the investigation-assistance workflow.

Expected AI:

-   case summary;
-   timeline summary;
-   signal explanation;
-   missing information;
-   investigative questions;
-   grounded report drafting.

Expected reporting:

-   structured report;
-   case/evidence references;
-   timeline;
-   findings;
-   unresolved questions;
-   report versions;
-   investigator review.

------------------------------------------------------------------------

# 60. Final verification prompt

Purpose: audit the complete project rather than assuming it works
because code exists.

Verify:

### Product

-   Is the system actually anti-doping intelligence/investigation
    software?
-   Is the main user journey complete?

### Frontend

-   routes work;
-   pages load;
-   data states exist;
-   API integration works;
-   no obvious broken UI.

### Backend

-   server starts;
-   API routes work;
-   authorization works;
-   validation works;
-   database access works.

### Database

-   migrations work;
-   schema is coherent;
-   seed/synthetic data works.

### Intelligence

-   rules execute;
-   ML executes;
-   temporal analysis works;
-   correlation works;
-   network signals work;
-   scores are explainable.

### Alerts

-   signals become alerts;
-   statuses work;
-   alert details explain themselves.

### Investigations

-   alert can become case;
-   evidence can be linked;
-   notes/tasks/findings work;
-   timeline works.

### AI

-   AI is grounded;
-   unsupported claims are avoided.

### Reports

-   report can be generated;
-   report is reviewable.

### Security

-   secrets are protected;
-   permissions are server-side;
-   audit events exist.

### Testing

-   tests pass;
-   build succeeds.

### Documentation

-   docs describe the actual implementation.

------------------------------------------------------------------------

# 61. Expected state after all prompts

The intended implementation state is:

``` text
Foundation                  → implemented baseline
Domain model                → implemented baseline
Synthetic data              → implemented baseline
Domain validation           → completed baseline
Repository management       → established baseline
Intelligence engine         → implemented
Alerts                      → implemented
Investigations              → implemented
AI assistance               → implemented
Reporting                   → implemented
Final verification          → verification/audit stage
```

However, the exact physical status must be checked against the
repository.

A prompt being executed is not evidence that every requested feature was
implemented correctly.

------------------------------------------------------------------------

# 62. Feature maturity classification

Use these labels during takeover:

``` text
PLANNED
SCAFFOLDED
MOCKED
PARTIALLY FUNCTIONAL
FUNCTIONAL
TESTED
PRODUCTION-READY
```

Do not call a UI-only feature functional merely because it renders.

Do not call a prototype production-ready without security, privacy,
reliability, compliance and operational validation.

------------------------------------------------------------------------

# 63. Current status matrix

  Area                       Intended state   Actual state to verify
  -------------------------- ---------------- ------------------------
  Product foundation         Complete         Verify
  Frontend foundation        Complete         Verify
  Backend foundation         Complete         Verify
  Domain model               Complete         Verify
  Synthetic data             Complete         Verify
  Domain validation          Complete         Verify
  Git repository             Established      Verify
  Rules                      Complete         Verify
  Isolation Forest           Complete         Verify
  Temporal analysis          Complete         Verify
  Cross-source correlation   Complete         Verify
  Network analysis           Complete         Verify
  Explainable scoring        Complete         Verify
  Alerts                     Complete         Verify
  Investigations             Complete         Verify
  Evidence                   Complete         Verify
  Tasks                      Complete         Verify
  Notes                      Complete         Verify
  Findings                   Complete         Verify
  AI assistant               Complete         Verify
  Reports                    Complete         Verify
  Audit                      Complete         Verify
  Authentication             Required         Verify
  RBAC                       Required         Verify
  Tests                      Required         Verify
  Docker                     Required         Verify
  CI                         Required         Verify
  Documentation              Required         Verify

------------------------------------------------------------------------

# 64. End-to-end demonstration scenario

A strong demo should use one synthetic scenario and trace it through the
system.

### Step 1 --- Athlete baseline

The synthetic athlete has mostly normal historical behavior.

### Step 2 --- New anomaly

A new unusual longitudinal pattern appears.

### Step 3 --- Travel context

A travel/whereabouts event occurs around the relevant period.

### Step 4 --- Independent intelligence

A separate intelligence report references a related entity.

### Step 5 --- Network context

The relationship graph shows a relevant connection.

### Step 6 --- Correlation

The intelligence engine correlates the information.

### Step 7 --- Priority

The system produces an explainable priority score, for example:

``` text
78 / 100 — VERY HIGH
```

### Step 8 --- Explanation

The investigator opens "Why Was This Flagged?" and sees the contributing
signals.

### Step 9 --- Decision

The investigator chooses to investigate.

### Step 10 --- Case

An investigation is created.

### Step 11 --- Evidence/work

The investigator adds evidence, notes and tasks and records findings.

### Step 12 --- AI

The AI produces a grounded case summary.

### Step 13 --- Report

A structured report draft is generated.

### Step 14 --- Review/close

The investigator reviews and closes or continues monitoring.

### Step 15 --- Audit

Important actions are visible in the audit history.

------------------------------------------------------------------------

# 65. Master definition of done

The product is functionally meaningful when a user can:

1.  Log in.
2.  Reach the dashboard.
3.  See synthetic anti-doping intelligence.
4.  Open an athlete/entity.
5.  Review history.
6.  Review testing/ABP information.
7.  Review intelligence.
8.  Review travel/whereabouts.
9.  Review relationships.
10. See an automated signal.
11. See the priority score.
12. Understand why it was flagged.
13. Open the alert.
14. Decide what to do.
15. Create an investigation.
16. Assign investigators.
17. Add evidence.
18. Add notes.
19. Create tasks.
20. Review/build the timeline.
21. Review relationships.
22. Record findings.
23. Ask the AI assistant for a grounded summary.
24. Generate a report.
25. Review the report.
26. Close or continue the investigation.
27. See the audit trail.

------------------------------------------------------------------------

# 66. Testing strategy

## Backend

Use pytest and HTTPX for:

-   unit tests;
-   API tests;
-   service tests;
-   authorization tests;
-   intelligence tests;
-   database/integration tests.

## Frontend

Use Vitest and React Testing Library for:

-   components;
-   hooks;
-   service behavior;
-   state behavior;
-   key workflows.

## End-to-end

Use Playwright for:

-   login;
-   dashboard;
-   alert opening;
-   case creation;
-   investigation workflow;
-   report generation.

------------------------------------------------------------------------

# 67. Important test cases

## Authentication

-   valid login;
-   invalid login;
-   unauthorized endpoint;
-   role restriction.

## Domain

-   athlete list/detail;
-   missing athlete;
-   filtering;
-   intelligence report validation;
-   travel record validation;
-   relationship creation.

## Intelligence

-   rule detection;
-   Isolation Forest execution;
-   signal persistence;
-   temporal correlation;
-   cross-source correlation;
-   network signal;
-   score calculation;
-   explanation generation.

## Alerts

-   creation;
-   filtering;
-   status changes;
-   dismissal;
-   monitoring;
-   case conversion.

## Investigations

-   create;
-   assign;
-   notes;
-   tasks;
-   evidence;
-   findings;
-   timeline;
-   close/reopen.

## AI

-   grounded summary;
-   missing information response;
-   no fabricated evidence.

## Reports

-   generation;
-   versioning;
-   invalid-case handling.

## Audit

-   important actions create audit records.

------------------------------------------------------------------------

# 68. Docker and deployment expectations

Prototype deployment should be simple.

Expected services:

``` text
frontend
backend
postgres
```

ML processing can remain inside the backend/module or be separated only
if the existing architecture genuinely benefits from it.

Use Docker Compose.

Do not introduce Kubernetes or a distributed infrastructure stack merely
for demonstration.

------------------------------------------------------------------------

# 69. Infrastructure non-goals

The prototype intentionally does not require:

-   Kubernetes;
-   Kafka;
-   microservices;
-   large cloud infrastructure;
-   complex distributed event buses;
-   real production ADAMS integration;
-   production whistleblower infrastructure;
-   autonomous enforcement.

These can be future production considerations.

------------------------------------------------------------------------

# 70. Logging requirements

Logs should help diagnose:

-   API errors;
-   authentication failures;
-   intelligence-engine failures;
-   ML failures;
-   report-generation failures.

Never log unnecessarily:

-   passwords;
-   access tokens;
-   confidential source identities;
-   sensitive intelligence content.

------------------------------------------------------------------------

# 71. Configuration and secrets

Environment variables should hold configuration such as:

-   database URL;
-   secret keys;
-   authentication settings;
-   AI-provider settings;
-   environment mode.

The repository should contain `.env.example` with placeholders.

It must not contain real credentials.

------------------------------------------------------------------------

# 72. Data lineage requirements

For any alert, an investigator/developer should be able to trace:

``` text
Alert
 ↓
Priority Score
 ↓
Score Components
 ↓
Signals
 ↓
Source Records
 ↓
Original Synthetic Data
```

For any case:

``` text
Case
 ↓
Triggering Alert
 ↓
Signals
 ↓
Evidence
 ↓
Notes
 ↓
Tasks
 ↓
Findings
 ↓
Report
 ↓
Audit History
```

This is essential to explainability and trust.

------------------------------------------------------------------------

# 73. Investigator feedback loop

Investigator decisions can later be used for evaluation.

Example:

``` text
Alert
 ↓
Investigator Review
 ↓
Useful / False Positive / Insufficient / Monitor
 ↓
Feedback Dataset
 ↓
Future Evaluation
```

Do not automatically retrain a production model from investigator
feedback without model governance.

------------------------------------------------------------------------

# 74. Model governance

Future model changes should record:

-   model purpose;
-   feature set;
-   data version;
-   model version;
-   threshold;
-   evaluation results;
-   known limitations;
-   false-positive behavior.

Never silently replace the model while leaving historical alerts without
their original model metadata.

------------------------------------------------------------------------

# 75. Rule governance

Rules should be versioned.

Example:

``` text
Rule: TEMPORAL_TEST_INTELLIGENCE_CORRELATION
Version: 1.2
Status: Active
```

Historical alerts should retain the rule version that generated them.

------------------------------------------------------------------------

# 76. Future production considerations

A production implementation would require substantially more work in:

-   privacy compliance;
-   legal review;
-   data-sharing agreements;
-   real identity management;
-   ADAMS interoperability;
-   secure source communication;
-   evidence integrity;
-   encryption;
-   key management;
-   infrastructure security;
-   monitoring;
-   incident response;
-   model governance;
-   bias testing;
-   operational validation.

These are future requirements and must not be falsely represented as
already solved by a prototype.

------------------------------------------------------------------------

# 77. What should NOT be changed without a reason

Do not casually replace:

-   the modular-monolith architecture;
-   the domain model;
-   the intelligence workflow;
-   the human-in-the-loop principle;
-   the synthetic-data policy;
-   explainable scoring;
-   alert-to-investigation workflow;
-   audit requirements;
-   API/service separation.

Do not rewrite the project just to make it look different.

------------------------------------------------------------------------

# 78. What can be extended

Good extension points include:

-   new intelligence-source adapters;
-   improved entity resolution;
-   additional detection rules;
-   additional anomaly models;
-   improved temporal algorithms;
-   graph metrics;
-   better dashboards;
-   additional reports;
-   AI providers;
-   secure integrations;
-   additional roles;
-   multi-tenancy;
-   stronger evidence integrity.

------------------------------------------------------------------------

# 79. Takeover procedure for a new developer/coding agent

A new agent must not immediately rewrite the project.

Follow this sequence:

``` text
Read Handover
      ↓
Inspect Repository
      ↓
Run Application
      ↓
Run Tests
      ↓
Inspect Database
      ↓
Inspect Synthetic Data
      ↓
Trace One Alert End-to-End
      ↓
Trace One Investigation End-to-End
      ↓
Inspect AI Grounding
      ↓
Inspect Audit Trail
      ↓
Create Gap Analysis
      ↓
Implement Highest-Value Gaps
      ↓
Retest
      ↓
Update Documentation
      ↓
Commit
```

------------------------------------------------------------------------

# 80. First repository audit

Inspect:

``` text
git status
git branch
git log --oneline --decorate -20
git remote -v
```

Then inspect:

1.  root directory;
2.  package manifests;
3.  frontend source;
4.  backend source;
5.  database models;
6.  migrations;
7.  seed scripts;
8.  synthetic data;
9.  ML code;
10. API routes;
11. authentication;
12. RBAC;
13. alert logic;
14. investigation logic;
15. evidence;
16. reports;
17. AI integration;
18. audit;
19. tests;
20. Docker;
21. CI;
22. documentation.

------------------------------------------------------------------------

# 81. Runtime verification

Frontend checks should include the actual commands configured by the
repository, typically equivalents of:

``` bash
pnpm install
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Backend checks typically include:

``` bash
pytest
```

Database checks may include:

``` bash
alembic upgrade head
```

Docker may include:

``` bash
docker compose up --build
```

Use the repository's actual scripts if they differ.

------------------------------------------------------------------------

# 82. Repository health checks

Verify:

-   correct remote;
-   correct branch;
-   understood working tree;
-   no credentials;
-   no real sensitive data;
-   no accidental build artifacts;
-   meaningful commit history;
-   reproducible setup.

------------------------------------------------------------------------

# 83. Final gap-analysis format

After inspection, classify each major capability as:

``` text
WORKING
PARTIAL
MOCKED
BROKEN
MISSING
```

Then prioritize:

### P0 --- blocks core demo

Examples:

-   application does not start;
-   database unavailable;
-   authentication broken;
-   alert cannot be generated;
-   case cannot be created.

### P1 --- weakens core product

Examples:

-   score not explainable;
-   evidence not linked;
-   timeline broken;
-   AI ungrounded;
-   report broken.

### P2 --- polish/extension

Examples:

-   better filters;
-   additional charts;
-   improved UI;
-   additional scenarios.

------------------------------------------------------------------------

# 84. Core demo checklist

Before a demonstration, verify this exact path:

``` text
[ ] Login
[ ] Dashboard
[ ] Synthetic data visible
[ ] Athlete/entity profile
[ ] Testing/ABP history
[ ] Intelligence report
[ ] Travel/whereabouts
[ ] Relationships
[ ] Automated signal
[ ] Explainable score
[ ] Alert
[ ] Investigator decision
[ ] Investigation creation
[ ] Evidence
[ ] Notes
[ ] Tasks
[ ] Timeline
[ ] Findings
[ ] AI summary
[ ] Report
[ ] Audit trail
```

If this path works, the core product story is demonstrated.

------------------------------------------------------------------------

# 85. Important product-story wording

Recommended explanation:

> **"We are not building an AI that declares an athlete guilty. We are
> building an intelligence system that helps investigators identify
> which cases deserve attention, explains why, connects the supporting
> information, and gives them the tools to investigate those cases."**

This wording captures the central product philosophy.

------------------------------------------------------------------------

# 86. Key technical distinctions

The system must maintain these boundaries:

``` text
Raw data
   ↓
Processed information
   ↓
Machine/statistical signal
   ↓
Alert
   ↓
Human investigation
   ↓
Evidence-backed finding
   ↓
Reviewed report
```

The machine does not skip directly from raw data to guilt.

------------------------------------------------------------------------

# 87. Security and privacy handover rules

Any future coding agent must:

1.  Use synthetic data unless explicitly authorized otherwise.
2.  Never commit real credentials.
3.  Never create realistic personal data that could accidentally
    identify a real person.
4.  Never expose confidential-source identity unnecessarily.
5.  Enforce authorization server-side.
6.  Audit sensitive actions.
7.  Treat uploaded intelligence as untrusted data.
8.  Protect the AI layer from prompt injection.
9.  Never use AI output as an automatic enforcement decision.
10. Preserve historical evidence and audit information.

------------------------------------------------------------------------

# 88. Code-quality rules for continuation

Future changes should maintain:

-   TypeScript strictness;
-   Python typing;
-   reusable components;
-   small focused functions;
-   clear names;
-   minimal duplication;
-   service/domain separation;
-   meaningful tests;
-   no unnecessary abstractions;
-   no needless infrastructure.

When a feature changes, update the relevant documentation.

------------------------------------------------------------------------

# 89. Documentation rules for continuation

Documentation must distinguish:

``` text
Implemented
vs
Mocked
vs
Planned
```

Never document planned functionality as implemented.

The README should describe:

-   product purpose;
-   user journey;
-   architecture;
-   setup;
-   environment configuration;
-   database;
-   intelligence engine;
-   testing;
-   limitations.

------------------------------------------------------------------------

# 90. What the project is ultimately demonstrating

The project demonstrates that an anti-doping investigation platform can
move from fragmented intelligence to an actionable, explainable
investigative workflow.

The key value is not the ML model alone.

The key value is the combination of:

``` text
Multi-source intelligence
        +
Longitudinal analysis
        +
Rules
        +
ML anomaly detection
        +
Temporal correlation
        +
Network analysis
        +
Explainable prioritization
        +
Alerting
        +
Investigation management
        +
Evidence management
        +
AI assistance
        +
Reporting
        +
Auditability
```

------------------------------------------------------------------------

# 91. Final architectural picture

``` text
                           USER
                            │
                            ▼
                 ┌────────────────────┐
                 │ React Investigation│
                 │      Workspace     │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │    FastAPI API     │
                 └─────────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
     Auth/RBAC         Domain Services    Investigation
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │ Intelligence Engine│
                 ├────────────────────┤
                 │ Rules              │
                 │ ML                 │
                 │ Temporal           │
                 │ Correlation        │
                 │ Network            │
                 │ Scoring            │
                 │ Explainability     │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │     PostgreSQL     │
                 └────────────────────┘

Sources:
Testing / ABP / Intelligence / Travel / Relationships / History
                           │
                           ▼
                 Intelligence Engine
```

------------------------------------------------------------------------

# 92. Final master checklist

## Product

-   [ ] SIH1721 alignment preserved.
-   [ ] Product is clearly intelligence + investigation, not merely
    detection.
-   [ ] Human-in-the-loop preserved.

## Data

-   [ ] Synthetic data used.
-   [ ] Multiple source types represented.
-   [ ] Longitudinal history represented.
-   [ ] Relationships represented.
-   [ ] Data lineage traceable.

## Intelligence

-   [ ] Rules implemented.
-   [ ] Isolation Forest implemented.
-   [ ] Temporal correlation implemented.
-   [ ] Cross-source correlation implemented.
-   [ ] Network signals implemented.
-   [ ] Weighted score implemented.
-   [ ] Score explanation implemented.
-   [ ] Rule/model version metadata stored.

## Alerts

-   [ ] Signals generate alerts.
-   [ ] Alert status workflow works.
-   [ ] Alert explanations work.
-   [ ] Investigator decisions recorded.

## Investigations

-   [ ] Alert can become a case.
-   [ ] Assignment works.
-   [ ] Evidence works.
-   [ ] Notes work.
-   [ ] Tasks work.
-   [ ] Timeline works.
-   [ ] Findings work.
-   [ ] Relationship context works.

## AI

-   [ ] AI is grounded.
-   [ ] AI does not fabricate.
-   [ ] AI cannot make final guilt decisions.
-   [ ] AI output can be reviewed.

## Reporting

-   [ ] Report generated from case data.
-   [ ] Evidence references included.
-   [ ] Findings included.
-   [ ] Report versioning/review supported.

## Security

-   [ ] Authentication works.
-   [ ] RBAC works.
-   [ ] Backend authorization works.
-   [ ] Secrets excluded from Git.
-   [ ] Audit logging works.
-   [ ] Sensitive source information is controlled.

## Engineering

-   [ ] Frontend builds.
-   [ ] Backend runs.
-   [ ] Database migrations work.
-   [ ] Tests pass.
-   [ ] Docker works.
-   [ ] CI works.
-   [ ] Documentation matches reality.

------------------------------------------------------------------------

# 93. Final handover status

The project has moved beyond the idea stage. The product definition,
domain model, architecture, intelligence strategy, scoring model,
investigation workflow, AI role, reporting concept, security principles,
synthetic-data strategy, repository strategy, and staged coding-agent
implementation plan have all been established.

The coding-agent prompts were designed to progressively turn that
specification into an end-to-end prototype.

The current source of truth hierarchy is:

``` text
1. Actual repository/runtime
       ↓
2. This HANDOVER.md for intended architecture/product behavior
       ↓
3. Original implementation prompts for stage-specific intent
```

If the repository differs from this handover, inspect the difference
before changing anything. Do not blindly rewrite the repository to match
documentation.

------------------------------------------------------------------------

# 94. Immediate next action

The next engineering action is **verification, not redevelopment**.

Perform:

``` text
Repository inspection
        ↓
Runtime startup
        ↓
Database verification
        ↓
Synthetic-data verification
        ↓
Intelligence-engine verification
        ↓
Alert verification
        ↓
Investigation verification
        ↓
AI grounding verification
        ↓
Report verification
        ↓
Audit verification
        ↓
Test suite
        ↓
Gap analysis
```

Only after this should additional implementation begin.

------------------------------------------------------------------------

# 95. Final statement

The intended product is:

> **A secure, explainable, human-in-the-loop anti-doping intelligence
> and investigations platform that connects fragmented information,
> identifies meaningful investigative signals, explains why they matter,
> and provides investigators with the complete workflow to examine,
> document and report those leads.**

The central principle remains:

> **Find the signals that matter, explain why they matter, connect the
> evidence, and give investigators the tools to investigate --- without
> replacing human judgment.**

------------------------------------------------------------------------

**END OF HANDOVER**
