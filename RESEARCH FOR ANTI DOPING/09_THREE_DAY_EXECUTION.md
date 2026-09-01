# 72-Hour Execution Plan

## Absolute rule

No architecture experimentation after Day 1.

No new major features after Day 3 begins.

---

# DAY 1

## Hour 0–1
Repository + environment.

## Hour 1–3
Backend skeleton + database + migrations.

## Hour 3–5
Auth + RBAC.

## Hour 5–8
Models + seed data.

## Hour 8–11
Athlete APIs + intelligence APIs.

## Hour 11–14
React shell + routing + auth.

## Hour 14–18
Dashboard + athlete search/profile.

## Hour 18–21
Timeline + basic alerts.

### Day 1 exit criteria

User can:

```text
login
→ dashboard
→ search athlete
→ open athlete
→ see synthetic intelligence/timeline
```

---

# DAY 2

## Hour 0–3
Rule engine.

## Hour 3–6
Feature engineering + Isolation Forest.

## Hour 6–8
Scoring.

## Hour 8–11
Correlation engine.

## Hour 11–14
Alert UI.

## Hour 14–18
Investigation workspace.

## Hour 18–20
Evidence + notes + tasks.

## Hour 20–22
Relationship graph.

### Day 2 exit criteria

```text
data
→ rules
→ ML
→ correlation
→ score
→ alert
→ case
→ graph
```

works.

---

# DAY 3

## Hour 0–3
Reports + audit.

## Hour 3–5
AI assistant.

## Hour 5–8
Tests.

## Hour 8–11
Security/RBAC testing.

## Hour 11–14
UI polish.

## Hour 14–17
Demo data and deterministic scenario.

## Hour 17–20
Bug fixes.

## Hour 20–22
Presentation + final rehearsal.

---

# Feature Freeze

No new:
- databases;
- services;
- algorithms;
- pages;
- integrations.

Only bug fixes after freeze.

---

# Team Parallelization

If 4 people:

### Person 1
Backend + DB.

### Person 2
Frontend.

### Person 3
ML/rules/correlation.

### Person 4
Investigation UX + graph + testing/documentation.

If 3:

### Person 1
Backend/DB.

### Person 2
Frontend.

### Person 3
Analytics + testing.

---

# Demo Order

1. Login.
2. Dashboard.
3. Open high-priority alert.
4. Explain score.
5. Open athlete.
6. Timeline.
7. Relationship graph.
8. Source intelligence.
9. Create case.
10. Add evidence.
11. Add task.
12. AI summary.
13. Generate report.
14. Change case status.
15. Show audit trail.

---

# Final Demo Script

Problem:

> "Anti-doping intelligence is not limited to laboratory results. Information may exist across multiple sources, and the investigative challenge is connecting those signals."

Solution:

> "Our platform converts fragmented intelligence into explainable investigation leads."

Demo:

> "This athlete has multiple independent signals within a 45-day window."

Then show:
- rules;
- anomaly;
- correlation;
- score.

Then:

> "The system does not declare guilt. It gives the investigator an explainable lead and the evidence behind it."

Open case.

> "The investigator can now manage evidence, tasks, relationships, notes and reporting in one workspace."

Finish:

> "The architecture is designed to integrate authorized operational systems in the future, while today's prototype uses synthetic data."

---

# Final quality gate

Before presentation:

- no broken routes;
- no fake buttons;
- no hardcoded dashboard numbers unless explicitly labeled demo fixtures;
- no console errors;
- no secrets in repository;
- all critical APIs tested;
- seeded demo works from a clean database;
- Docker Compose starts;
- report generation works;
- graph works;
- score explanation works;
- false-positive case works.
