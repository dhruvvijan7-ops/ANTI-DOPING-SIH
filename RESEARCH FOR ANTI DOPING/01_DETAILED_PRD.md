# Detailed Product Requirements Document

## 1. Product Definition

### Name
Working name: **CleanSport Intelligence**  
Alternative names can be selected later.

### Category
Anti-Doping Intelligence & Investigation Software.

### Primary stakeholder
National Anti-Doping Organization / authorized intelligence and investigation team.

### Primary user
Authorized investigator and intelligence analyst.

---

# 2. User Problems

## Investigator problems

1. Information is distributed across sources.
2. Important relationships are difficult to discover.
3. Analysts must manually correlate events.
4. High-volume intelligence creates prioritization problems.
5. Evidence and investigation notes can become fragmented.
6. It can be difficult to explain why an intelligence lead was prioritized.
7. Investigation progress requires consistent case documentation.

## Analyst problems

1. Need a single intelligence view.
2. Need repeatable detection rules.
3. Need anomaly detection.
4. Need source assessment.
5. Need relationship discovery.
6. Need a way to distinguish noise from actionable leads.

---

# 3. User Stories

## Authentication
**US-001:** As an investigator, I want secure login so unauthorized people cannot access intelligence.

**US-002:** As an administrator, I want roles so investigators cannot perform administrative operations.

## Intelligence
**US-010:** As an analyst, I want to import intelligence records so multiple sources can be analyzed together.

**US-011:** As an analyst, I want each record to retain its source so I can assess provenance.

**US-012:** As an analyst, I want to link a record to an athlete so intelligence can be aggregated.

## Analytics
**US-020:** As an analyst, I want rules to detect predefined patterns.

**US-021:** As an analyst, I want anomaly detection to highlight unusual patterns.

**US-022:** As an investigator, I want to know why an alert was generated.

**US-023:** As an investigator, I want related entities visualized.

## Investigation
**US-030:** As an investigator, I want to convert an intelligence lead into a case.

**US-031:** As an investigator, I want to assign a case.

**US-032:** As an investigator, I want to record evidence.

**US-033:** As an investigator, I want to document investigative actions.

**US-034:** As an investigator, I want a chronological timeline.

**US-035:** As an investigator, I want to generate a report.

## AI
**US-040:** As an investigator, I want an AI-generated summary of known case information.

**US-041:** As an investigator, I want suggested investigation questions.

---

# 4. Detailed Functional Requirements

## FR-AUTH-001
The system shall require authentication before protected pages load.

## FR-AUTH-002
The backend shall validate authentication independently of frontend route guards.

## FR-AUTH-003
Passwords shall never be stored in plaintext.

## FR-AUTH-004
The system shall support at least four roles:
- Administrator
- Investigator
- Intelligence Analyst
- Viewer

## FR-INTEL-001
Each intelligence record shall have a unique ID.

## FR-INTEL-002
Each intelligence record shall contain:
- source;
- source type;
- creation time;
- ingestion time;
- subject;
- description;
- confidentiality;
- reliability;
- status.

## FR-INTEL-003
Records shall support links to multiple entities.

## FR-INTEL-004
Duplicate records shall be detectable using source ID/hash.

## FR-INTEL-005
The system shall preserve the original source record ID.

## FR-ANALYSIS-001
Analysis runs shall be identifiable by run ID.

## FR-ANALYSIS-002
Each run shall store:
- timestamp;
- model version;
- rule versions;
- dataset/version;
- parameters.

## FR-ANALYSIS-003
Rules shall return:
- rule ID;
- indicator;
- severity;
- evidence references;
- explanation.

## FR-ANALYSIS-004
ML output shall be stored separately from deterministic rules.

## FR-ANALYSIS-005
A composite priority score shall be explainable.

## FR-ALERT-001
Alerts shall be generated when configurable thresholds are reached.

## FR-ALERT-002
Alerts shall support:
- New
- Reviewed
- Dismissed
- Escalated
- Converted to case

## FR-CASE-001
An investigation shall have a unique case ID.

## FR-CASE-002
A case shall support multiple subjects.

## FR-CASE-003
A case shall support multiple intelligence records.

## FR-CASE-004
A case shall support multiple evidence objects.

## FR-CASE-005
A case shall support tasks and notes.

## FR-CASE-006
A case shall have a lifecycle state.

## FR-CASE-007
A case shall maintain an audit trail.

## FR-REPORT-001
The report generator shall summarize:
- subject;
- case status;
- intelligence;
- indicators;
- evidence;
- timeline;
- relationships;
- investigator findings.

---

# 5. Non-Functional Requirements

## Performance
Prototype target:
- dashboard API < 1 second under local demo load;
- athlete profile < 1 second;
- alert query < 1 second;
- analysis of 500 synthetic athletes < 10 seconds.

These are prototype engineering targets, not production SLAs.

## Availability
Local Docker environment should start with one command.

## Maintainability
Use modular backend packages.

## Testability
Critical detection/risk logic must be unit tested.

## Accessibility
Keyboard-accessible controls and sufficient text contrast.

## Reliability
Analysis failures must not corrupt source data.

## Observability
Backend logs should include request ID and analysis run ID.

---

# 6. Requirement Traceability

| SIH requirement | Product feature |
|---|---|
| Centralized database | PostgreSQL canonical store |
| Multiple data sources | Intelligence ingestion |
| Testing/ABP | Synthetic testing + marker records |
| Medical | Synthetic medical/TUE metadata |
| Social | Synthetic OSINT reports |
| Financial | Synthetic transaction indicators, not real data |
| Travel | Travel events |
| AI/ML | Isolation Forest |
| Pattern/anomaly | Rules + anomaly |
| Risk assessment | Explainable priority score |
| Visualization | Charts + graph + timeline |
| Investigation management | Case workspace |
| Evidence management | Evidence module |
| Collaboration | Tasks/assignments/notes |
| Reporting | Report generator |
| Confidential communication | Prototype intake concept |
| Training/resources | Resource center |

---

# 7. Product Metrics

Prototype metrics:

- time to identify high-priority lead;
- percentage of alerts with explanations;
- percentage of alerts linked to evidence;
- case creation time;
- false-positive identification;
- analysis execution time;
- test pass rate.

Future operational metrics:
- analyst workload;
- alert precision;
- investigation cycle time;
- source corroboration rate;
- case conversion rate.
