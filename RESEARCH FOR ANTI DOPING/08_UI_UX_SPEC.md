# UI/UX Specification

## 1. Design Direction

Visual language:

**Intelligence operations center + investigative case-management system**

Avoid:
- sports fan UI;
- gamified design;
- excessive neon;
- generic admin dashboard.

Use:
- dark/light professional theme;
- high information density;
- clear severity hierarchy;
- restrained color use;
- strong typography;
- dense tables;
- timelines;
- graphs;
- evidence cards.

---

# 2. Navigation

```text
Overview
Intelligence
Alerts
Athletes
Investigations
Graph
Reports
Resources
Administration
```

---

# 3. Dashboard

### Header
- date
- search
- notifications
- user

### KPI
- active leads
- critical
- very high
- open investigations
- pending tasks

### Main panels
- priority trend
- alert distribution
- intelligence source mix
- recent alerts

### Right rail
- urgent investigations
- tasks due
- recent intelligence

---

# 4. Intelligence Inbox

Columns:
- ID
- received
- source
- subject
- type
- reliability
- confidentiality
- status
- linked entities

Actions:
- assess;
- link;
- correlate;
- create alert.

---

# 5. Alert Center

Filters:
- severity;
- sport;
- source;
- date;
- status;
- investigator.

Alert card:

```text
VERY HIGH
ATH-1047
Priority: 79.5

3 source categories
4 indicators
45-day correlation
2 network links

[Investigate]
```

---

# 6. Athlete Profile

Top:
```text
ATH-1047
Track & Field
Priority 79.5
VERY HIGH
```

Tabs:
- Overview
- Intelligence
- Testing
- Markers
- Travel
- Relationships
- Timeline
- Alerts
- Cases

---

# 7. Investigation Page

Three-column concept:

```text
LEFT
Case navigation

CENTER
Evidence / timeline / findings

RIGHT
Risk / entities / tasks / AI assistant
```

---

# 8. Relationship Graph

Use React Flow.

Features:
- zoom;
- pan;
- search;
- node filtering;
- relationship evidence;
- click-to-open.

Node types:
- athlete;
- coach;
- provider;
- team;
- event;
- report.

---

# 9. Timeline

Every event:
- timestamp;
- category;
- source;
- entity;
- severity;
- linked evidence.

Filters:
- testing;
- intelligence;
- travel;
- medical;
- relationship;
- investigation.

---

# 10. Report Preview

Sections:
1. Case metadata
2. Executive summary
3. Subject
4. Intelligence received
5. Analytical findings
6. Timeline
7. Relationships
8. Evidence
9. Investigator findings
10. Outcome

---

# 11. UX Safety

Never use UI language like:

**"AI detected a doper."**

Use:

**"High-priority intelligence lead."**

Never:

**"Guilty probability: 87%."**

Use:

**"Investigation-priority score: 87."**

---

# 12. Empty States

Every page needs useful empty states.

Example:

> No active high-priority intelligence. New intelligence will appear here after assessment.

---

# 13. Loading

Use:
- skeleton tables;
- chart placeholders;
- graph loading state.

Never show a blank page.

---

# 14. Error Handling

Display:
- actionable error;
- retry;
- request ID.

Example:

> Unable to load investigation. Retry or provide request ID REQ-1842 to an administrator.
