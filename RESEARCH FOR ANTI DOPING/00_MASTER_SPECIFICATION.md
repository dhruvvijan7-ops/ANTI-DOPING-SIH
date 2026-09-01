# ANTI-DOPING INTELLIGENCE & INVESTIGATION PLATFORM
## Master Product + Technical Specification
### SIH1721 — Intelligence and Investigations – Enhancing Anti-Doping Efforts

**Document status:** Detailed prototype baseline  
**Target:** 3-day functional prototype  
**Prototype principle:** 90% of the defined MVP workflow must be functional; no dead screens or fake buttons.

---

# 1. Executive Summary

The proposed platform is a software-only intelligence and investigation system for an Anti-Doping Organization. It is designed around the SIH1721 requirement to integrate multiple intelligence sources, apply advanced analytics and AI/ML, produce actionable intelligence, support investigations, manage evidence and protect confidential reporting.

The system is not intended to replace WADA ADAMS, NADA operational systems, laboratory systems or results-management systems. Instead, the prototype is an **intelligence-analysis and investigation layer**.

The platform transforms heterogeneous intelligence into an investigator-oriented workflow:

**Collect → Validate → Normalize → Resolve Entities → Detect → Correlate → Prioritize → Alert → Investigate → Evidence → Report → Outcome**

The central product object is not the athlete record. It is the **intelligence lead/investigation**.

---

# 2. Problem Statement

SIH1721 asks for a comprehensive intelligence and investigation system to enhance NADA's ability to detect, investigate and act upon doping violations. The statement calls for:

- centralized and scalable data storage;
- integration of testing results, Athlete Biological Passports and third-party information;
- additional external sources such as medical, social, financial and travel data;
- AI/ML analytics to identify patterns and anomalies;
- risk assessment;
- visualization;
- investigation management;
- evidence management;
- collaboration;
- automated reporting;
- secure confidential communication;
- investigator training/resources.

The official SIH listing identifies SIH1721 as a Software problem under Smart Automation and the provider as the Ministry of Youth Affairs & Sports. The detailed statement identifies NADA's Coordination Section/Department of Sports context. 

**Critical interpretation:** the system must convert information into actionable intelligence, not merely store information.

---

# 3. Product Vision

> Build a secure, explainable and investigator-centric intelligence platform that turns fragmented anti-doping information into traceable intelligence leads and evidence-linked investigations while keeping final investigative judgment with authorized humans.

---

# 4. Product Principles

## 4.1 Intelligence first
The system is an intelligence platform, not a generic athlete-management application.

## 4.2 Human in the loop
Algorithms prioritize and explain signals. Authorized investigators decide what action to take.

## 4.3 Explainability by default
Every alert and score must have visible contributing factors and source records.

## 4.4 Evidence traceability
Every analytical conclusion must be traceable to underlying records.

## 4.5 Privacy by design
Real sensitive athlete, medical, financial or confidential-source data must not be used in the prototype.

## 4.6 Least privilege
Users can access only the information and functions required by their role.

## 4.7 Reproducible analysis
Every score should retain model/rule versions and input references.

## 4.8 No guilt inference
A risk/priority score is not a probability of guilt and is not a sanctioning decision.

---

# 5. Existing Ecosystem and Position

The anti-doping ecosystem already contains mature systems.

## 5.1 WADA ADAMS

ADAMS is a secure web-based system that centralizes doping-control information including athlete whereabouts, testing history, laboratory results, Athlete Biological Passport information, TUEs and anti-doping rule-violation information.

**Our relationship to ADAMS:** upstream/peer ecosystem integration, not replacement.

Prototype assumption:

```text
Authorized ADAMS/API export
        ↓
Intelligence ingestion layer
        ↓
Normalization
        ↓
Correlation + analysis
```

For the prototype, use synthetic ADAMS-like records.

## 5.2 WADA Speak Up!

A confidential reporting mechanism for suspected doping misconduct.

**Our prototype:** demonstrate a controlled intelligence intake concept, but do not claim production-grade anonymous-source protection.

## 5.3 ITA REVEAL

REVEAL is a secure/confidential reporting platform. ITA states that reports are received, assessed and actioned by its Intelligence & Investigations team.

**Design lesson:** intake must be followed by assessment and action; a reporting form alone is not an intelligence platform.

## 5.4 Jade ICM

Jade ICM is a commercial investigations case-management platform used by regulatory/enforcement agencies, including anti-doping. Its capabilities include centralizing information, discovering lines of enquiry, managing evidence and visualizing relationships.

**Design lesson:** case management and evidence handling are established requirements. Our differentiator is the combination with a purpose-built anti-doping intelligence correlation and prioritization layer.

## 5.5 WADA SISP / GAIIN

WADA's European intelligence/investigation capability project created SISP for secure communication between NADO and law-enforcement participants and is being expanded through the Global Anti-Doping Intelligence & Investigations Network.

NADA India hosted WADA I&I workshops in 2025 and the GAIIN final conference in New Delhi in April 2026.

**Design lesson:** interoperability and collaboration are real domain requirements, but cross-organization infrastructure is out of scope for a 3-day prototype.

---

# 6. Product Scope

## 6.1 In scope

### Identity and access
- Login
- Roles
- Permissions
- Session management
- Audit logs

### Intelligence
- Synthetic multi-source ingestion
- Manual intelligence entry
- Source classification
- Source reliability metadata
- Information assessment
- Entity resolution
- Duplicate detection

### Analytics
- Configurable rules
- Feature extraction
- Isolation Forest anomaly detection
- Temporal correlation
- Cross-source correlation
- Relationship/network scoring
- Explainable priority scoring

### Operations
- Alert queue
- Triage
- Investigation creation
- Assignment
- Evidence
- Notes
- Tasks/actions
- Timeline
- Relationship graph
- Related cases
- Case status
- Reports

### AI assistance
- Case summarization
- Indicator explanation
- Investigation question suggestions
- Timeline summarization

### Resource center
- Investigation guidance
- Rule documentation
- Model/rule descriptions
- Training examples

---

# 7. Explicitly Out of Scope

- Real NADA/ADAMS production integration
- Real athlete personal data
- Real medical records
- Real financial transactions
- Real confidential-source identities
- Real law-enforcement data
- Autonomous enforcement
- Automatic sanctions
- Legal determinations
- Production anonymous communication infrastructure
- Production-grade national-scale infrastructure
- Mobile application
- Hardware
- Kubernetes
- Microservice fleet
- Real-time streaming infrastructure
- Deep neural network research
- Facial recognition
- General internet surveillance

---

# 8. Personas

## 8.1 Investigator

Primary workflow:

**Review lead → inspect subject → examine evidence → identify lines of enquiry → create case → assign tasks → document findings → report outcome**

Permissions:
- View assigned/authorized intelligence
- Create cases
- Add evidence
- Add notes
- Assign tasks
- Run analysis
- Change case status
- Generate reports

## 8.2 Intelligence Analyst

Primary workflow:

**Monitor intelligence → assess sources → correlate → analyze → create intelligence lead**

Permissions:
- Ingest intelligence
- Run analytics
- Review alerts
- Build/link relationships
- Create intelligence assessments
- Recommend cases

## 8.3 Administrator

- User management
- Role management
- Rule configuration
- Model version management
- Source configuration
- Audit review

## 8.4 Viewer/Auditor

- Read-only access to authorized records
- Report access
- Audit history access

---

# 9. Functional Architecture

```text
                         WEB CLIENT
                             |
                       API / HTTPS
                             |
                  +----------+----------+
                  |                     |
             AUTH/RBAC             APPLICATION
                                        |
       +-------------+-----------+------+-------+
       |             |           |              |
 Intelligence    Analytics   Investigations   Reporting
       |             |           |              |
       +-------------+-----------+--------------+
                             |
                        PostgreSQL
                             |
                +------------+------------+
                |            |            |
              Rules         ML        Correlation
                |            |            |
                +------------+------------+
```

---

# 10. Core Data Objects

- User
- Role
- Permission
- Athlete
- AthleteSupportPerson
- Team
- Organization
- TestEvent
- BiologicalMarkerObservation
- WhereaboutsEvent
- MedicalEvent
- TUERecord
- Supplement
- Provider
- TravelEvent
- IntelligenceReport
- Source
- SourceAssessment
- Relationship
- Indicator
- AnalysisRun
- Alert
- IntelligenceCluster
- Investigation
- Evidence
- InvestigationTask
- InvestigationNote
- InvestigationAction
- CaseOutcome
- Report
- AuditEvent
- ModelVersion
- RuleVersion

---

# 11. Intelligence Lifecycle

## Stage 1 — Collection

Accept:
- CSV
- JSON
- manual entry
- synthetic seeded records

Each record gets:
- source
- source type
- ingestion timestamp
- original record ID
- confidentiality classification
- integrity status

## Stage 2 — Validation

Check:
- required fields
- dates
- IDs
- numeric ranges
- duplicate source IDs
- schema version

## Stage 3 — Normalization

Convert source-specific formats to canonical structures.

Example:

```text
"athleteId": "A-1004"
"subject": "A-1004"
"participant": "1004"
```

→

```text
canonical_athlete_id = A-1004
```

## Stage 4 — Entity Resolution

Link:
- same athlete
- same coach
- same provider
- same event
- same organization

Prototype methods:
1. exact identifiers;
2. normalized names;
3. source IDs;
4. configurable deterministic matching.

Do not use fuzzy matching as the sole basis for a high-risk decision.

## Stage 5 — Assessment

Evaluate:
- source reliability;
- information quality;
- corroboration;
- recency;
- specificity.

## Stage 6 — Detection

Run:
- rules;
- anomaly model;
- temporal analysis;
- relationship analysis.

## Stage 7 — Correlation

Combine compatible signals into clusters.

## Stage 8 — Prioritization

Generate explainable investigation-priority score.

## Stage 9 — Human triage

Investigator/analyst decides:
- dismiss;
- monitor;
- request information;
- create case;
- escalate;
- link to existing case.

## Stage 10 — Investigation

Case workspace manages:
- evidence;
- tasks;
- notes;
- timeline;
- relationships;
- findings.

## Stage 11 — Outcome

Allowed prototype outcomes:
- Closed — no further action
- Closed — false positive
- Unsubstantiated
- Escalated
- Referred
- Further monitoring

Never allow AI to directly select "doping violation confirmed."

---

# 12. Dashboard Requirements

## KPI cards

- Total athletes
- Intelligence records
- Active alerts
- High-priority leads
- Open investigations
- Cases awaiting action
- False-positive rate
- Recent intelligence

## Charts

### Risk distribution
Low/moderate/high/very high/critical.

### Alerts over time
Daily/weekly.

### Source contribution
Testing / report / travel / medical / network / other.

### Investigation status
New / triage / active / awaiting information / closed.

### Top correlated entities
Athletes/support personnel/providers/teams.

---

# 13. Athlete Intelligence Page

Header:
- athlete ID
- sport
- team
- country
- priority score
- score trend
- investigation status

Tabs:
1. Overview
2. Testing
3. Biological markers
4. Whereabouts
5. Medical/TUE metadata
6. Travel
7. Supplements
8. Intelligence reports
9. Relationships
10. Timeline
11. Alerts
12. Cases

## Risk panel

Must show:
- score
- level
- model version
- date calculated
- score contributors
- supporting records

---

# 14. Alert Page

Each alert contains:

- Alert ID
- created time
- priority
- subject
- alert type
- triggered rules
- anomaly signal
- correlation cluster
- supporting records
- source assessments
- related entities
- recommended next step
- analyst decision

---

# 15. Investigation Workspace

## Header
- case ID
- title
- status
- priority
- investigator
- creation date
- due date

## Sections

### Overview
What is known.

### Intelligence
All linked leads.

### Evidence
Documents/records.

### Timeline
Chronological events.

### Relationships
Graph.

### Tasks
Investigation actions.

### Notes
Structured notes.

### Findings
Supporting and exculpatory evidence.

### Report
Generated summary.

### Audit
Immutable activity history.

---

# 16. Relationship Graph

Nodes:
- athlete
- coach
- doctor
- team
- supplement
- provider
- event
- organization
- report

Edges:
- coached by
- treated by
- member of
- associated with
- used
- supplied by
- reported by
- participated in
- related to

Node click opens entity details.

Edge click opens relationship evidence.

---

# 17. Evidence Model

Evidence must include:

- evidence ID
- type
- title
- description
- source
- collection time
- linked entity
- linked case
- hash/checksum for uploaded files where implemented
- confidentiality
- relevance
- status
- created by
- created time

Prototype evidence types:
- intelligence report
- test record
- travel record
- medical metadata
- communication record
- document
- image metadata
- external reference
- investigator observation

---

# 18. Audit Requirements

Log:
- login
- failed login
- logout
- record view for protected records
- intelligence creation
- intelligence update
- alert creation
- alert dismissal
- case creation
- case assignment
- evidence addition
- evidence modification
- report generation
- role changes
- rule changes
- model changes

Audit fields:
- actor
- action
- object type
- object ID
- timestamp
- IP/device metadata where appropriate
- before/after summary where appropriate

---

# 19. Security

## Authentication
- Password hashing
- Access tokens
- Token expiration
- Logout/revocation strategy
- Rate limiting on login

## Authorization
Enforce RBAC on the backend.

## Input validation
Pydantic schemas.

## Database
Parameterized ORM queries.

## Secrets
Environment variables only.

## Confidentiality
Every intelligence record has a classification:

- PUBLIC
- INTERNAL
- CONFIDENTIAL
- RESTRICTED

Access must be role/permission controlled.

## Privacy
The system should collect only what is needed for the prototype.

NADA India explicitly states that anti-doping personal information must be processed consistently with applicable anti-doping privacy standards and law. WADA's privacy standard emphasizes appropriate protection of personal information.

---

# 20. AI Assistant

The assistant is retrieval-grounded.

Allowed:
- summarize case;
- explain score;
- summarize timeline;
- identify linked entities;
- suggest questions;
- draft report.

Not allowed:
- invent evidence;
- create allegations;
- make legal conclusions;
- automatically sanction;
- claim guilt.

Every generated summary should reference the underlying case records internally.

---

# 21. Prototype Acceptance Test

A complete demo must execute:

```text
LOGIN
 ↓
DASHBOARD
 ↓
HIGH PRIORITY ALERT
 ↓
ATHLETE PROFILE
 ↓
SCORE EXPLANATION
 ↓
TIMELINE
 ↓
RELATIONSHIP GRAPH
 ↓
SOURCE RECORDS
 ↓
CREATE CASE
 ↓
ADD EVIDENCE
 ↓
ADD NOTE
 ↓
CREATE TASK
 ↓
AI SUMMARY
 ↓
GENERATE REPORT
 ↓
UPDATE CASE STATUS
 ↓
AUDIT LOG
```

If any of these is only a visual mock, the MVP is not complete.

---

# 22. Demo Scenario

Use a fictional athlete:

**ATH-1047**

Synthetic indicators:
- repeated missed testing/whereabouts event;
- abnormal longitudinal marker pattern;
- multiple intelligence reports;
- shared provider relationship;
- temporal clustering;
- unusual travel sequence;
- related support-personnel connection.

The system should generate:

**Priority = VERY HIGH**

The investigator then examines each contributor, opens a case, links evidence and ultimately records a human decision.

Include a second synthetic athlete who initially receives a high score but is later marked **False Positive** to demonstrate that the system does not equate risk with guilt.

---

# 23. Prototype Dataset

Recommended:
- 500 athletes
- 80 support personnel
- 40 teams
- 30 providers
- 100 supplements
- 5,000 test events
- 3,000 travel events
- 2,000 intelligence reports
- 1,500 relationships
- 200 injected suspicious patterns
- 50 known synthetic investigation cases
- 20 false-positive cases

Dataset distribution should be intentionally imbalanced so the analytics workflow resembles a triage system.

---

# 24. Engineering Constraint

The three-day build must prioritize vertical completeness over infrastructure complexity.

**Build fewer modules completely rather than many modules partially.**

Priority:

P0 = required for end-to-end demo  
P1 = important for credibility  
P2 = future enhancement

---

# 25. P0 Features

- Auth
- RBAC
- Dashboard
- Athlete search/profile
- Synthetic ingestion
- Rules
- ML anomaly
- Correlation
- Score
- Alerts
- Cases
- Evidence
- Timeline
- Graph
- Notes
- Reports
- Audit

---

# 26. P1

- Advanced source assessment
- Saved searches
- configurable dashboards
- report templates
- model comparison
- case assignment queues
- resource center
- notifications

---

# 27. P2

- Real ADAMS integration
- secure external partner sharing
- production confidential-source platform
- streaming ingestion
- advanced NLP
- graph database
- cloud deployment
- mobile app
