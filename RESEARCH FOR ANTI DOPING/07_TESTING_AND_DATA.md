# Testing Strategy + Synthetic Data Specification

# 1. Testing Philosophy

Every critical capability must be tested against known synthetic scenarios.

Do not test only whether an API returns 200.

Test whether the intelligence system produces the expected investigative behavior.

---

# 2. Synthetic Population

## Base population

500 athletes.

Distribution:
- 400 normal
- 50 mildly anomalous
- 25 suspicious-pattern
- 15 high-risk injected
- 10 false-positive scenarios

These are artificial labels for evaluation.

---

# 3. Support Network

- 80 coaches/support personnel
- 30 medical/provider entities
- 40 teams
- 100 supplements/providers
- 20 organizations

Create both normal and intentionally clustered relationships.

---

# 4. Event Dataset

### Testing
5,000 events.

### Whereabouts
4,000 events.

### Travel
3,000 events.

### Medical/TUE metadata
1,500 events.

### Intelligence reports
2,000 records.

### Relationships
1,500+ edges.

---

# 5. Injection Scenarios

## Scenario 1 — Normal athlete
No meaningful correlated signals.

Expected:
LOW.

## Scenario 2 — Single anomaly
One unusual travel pattern.

Expected:
LOW/MODERATE.

## Scenario 3 — Repeated testing issue
Multiple synthetic missed events.

Expected:
MODERATE/HIGH.

## Scenario 4 — Longitudinal anomaly
Synthetic marker deviations.

Expected:
HIGH.

## Scenario 5 — Multi-source
Testing + intelligence + travel.

Expected:
VERY HIGH.

## Scenario 6 — Network cluster
Three athletes share support/provider relationship and related indicators.

Expected:
VERY HIGH/CRITICAL.

## Scenario 7 — False positive
Strong statistical anomaly but legitimate explanation in synthetic record.

Expected:
High initial score → human review → FALSE POSITIVE.

## Scenario 8 — Duplicate report
Same source record submitted twice.

Expected:
deduplicate.

## Scenario 9 — Unreliable source
Low-quality source with no corroboration.

Expected:
reduced priority.

---

# 6. Unit Tests

## Rule tests
- threshold boundary;
- missing fields;
- duplicate records;
- date windows.

## ML tests
- deterministic random seed;
- model loads;
- score range;
- expected injected anomalies ranked highly.

## Correlation tests
- same entity;
- different entities;
- date-window boundary;
- unrelated records.

## Risk tests
- component normalization;
- weighted calculation;
- threshold classification.

---

# 7. Integration Tests

1. Import intelligence.
2. Run analysis.
3. Alert generated.
4. Open alert.
5. Convert to case.
6. Add evidence.
7. Add note.
8. Add task.
9. Change status.
10. Generate report.
11. Audit events exist.

---

# 8. End-to-End Test

Scenario:

```text
Synthetic report
      ↓
Athlete A-1047
      ↓
3 corroborating signals
      ↓
Analysis
      ↓
Priority 79.5
      ↓
Very High alert
      ↓
Investigator review
      ↓
Case created
      ↓
Evidence linked
      ↓
Graph shows provider/support relationship
      ↓
AI summarizes evidence
      ↓
Report generated
      ↓
Case marked under investigation
```

---

# 9. Acceptance Criteria

### Analytics
- every alert has explanation;
- every score has source records;
- every model run is versioned.

### Investigation
- case can be created from alert;
- evidence persists;
- notes persist;
- timeline updates;
- graph renders.

### Security
- unauthorized role cannot modify cases;
- restricted record access is denied;
- audit events are generated.

### Reliability
- analysis can be rerun;
- failures do not destroy source data.

---

# 10. Demo Evaluation Dashboard

Optional developer page showing:

- precision;
- recall;
- F1;
- false positives;
- runtime;
- top-ranked injected cases.

Label clearly:

**Synthetic prototype evaluation — not real-world model performance.**
