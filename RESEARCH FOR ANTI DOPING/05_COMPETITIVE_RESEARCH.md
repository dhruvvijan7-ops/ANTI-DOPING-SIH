# Competitive & Existing Product Research

## 1. Why competitive research matters

The SIH problem is not asking for a product category that has never existed. Anti-doping organizations already use data, reporting, intelligence, investigation and case-management systems.

Therefore the prototype must answer:

1. What already exists?
2. What does it do?
3. What is missing or fragmented?
4. What are we demonstrating?
5. Why would an investigator use this?

---

# 2. WADA ADAMS

## What it is

ADAMS is WADA's secure web-based anti-doping administration and management ecosystem.

Public WADA material describes centralized information including:
- whereabouts;
- testing history;
- laboratory results;
- Athlete Biological Passport;
- TUEs;
- anti-doping rule violations.

WADA's current application status page also exposes ADAMS Web, Athlete Central, DCO Central, Next Gen Athlete Biological Passport, reporting, IAM and APIs.

## Strengths

- authoritative anti-doping operational ecosystem;
- broad data coverage;
- established stakeholder ecosystem;
- privacy/security focus;
- APIs and connected applications.

## Weakness for our prototype opportunity

We should not attempt to recreate its operational scope.

Our project should be an intelligence/analytics layer:

```text
ADAMS-like data
       ↓
Intelligence platform
       ↓
Correlation
       ↓
Investigator
```

---

# 3. WADA Speak Up!

## Purpose
Confidential reporting of suspected doping misconduct.

## Lessons
- source protection matters;
- reporting is only the beginning;
- confidentiality must persist through processing;
- two-way communication may be needed.

## Prototype implementation

Create:

**Intelligence Intake**

with:
- anonymous toggle;
- category;
- description;
- entities;
- date;
- attachments;
- confidentiality;
- acknowledgement.

Do not claim real anonymity.

---

# 4. ITA REVEAL

## Purpose
Secure/confidential reporting platform.

ITA states that received information is reviewed, assessed and actioned by the Intelligence & Investigations team.

Its public workflow includes:
1. reporter management/protection;
2. reporter and information assessment;
3. action/triage.

## Design lesson

Our system should have a similar internal progression:

```text
Received
 ↓
Protected intake
 ↓
Assessment
 ↓
Correlation
 ↓
Triage
 ↓
Action
```

---

# 5. Jade ICM

## Purpose
Investigation case management.

Capabilities publicly described:
- centralize/share information;
- discover lines of enquiry;
- manage evidence;
- visualize relationships;
- assign/track case work;
- manage investigative workflow;
- close investigations.

## Design lesson

Our case page should contain:
- evidence;
- notes;
- tasks;
- relationships;
- timeline;
- investigative lines of enquiry;
- report.

## Differentiation

Jade is a mature generic/regulatory investigation platform.

Our prototype demonstrates a domain-specific intelligence engine before the case stage.

---

# 6. WADA SISP

Secure communication platform created through the European I&I project for NADO/law-enforcement participants.

## Design lesson

Future architecture should allow:
- secure sharing;
- partner organizations;
- permissions;
- sharing agreements;
- access logging.

Not part of the 3-day build.

---

# 7. GAIIN

WADA is expanding anti-doping intelligence/investigation collaboration globally. NADA India hosted workshops in 2025 and the GAIIN final conference in April 2026.

## Strategic implication

The timing strengthens the relevance of an intelligence-led platform.

However, do not claim the prototype is an official GAIIN system.

---

# 8. Academic prototype risk

A recent academic prototype called NADARAI demonstrates that:
- synthetic data;
- React;
- FastAPI;
- relational storage;
- deterministic rules;
- Isolation Forest;
- composite risk scores

can form an anti-doping intelligence prototype.

Therefore our project needs additional depth.

---

# 9. Our Differentiation

### Existing systems already provide:
- data management;
- reporting;
- secure intake;
- case management;
- operational anti-doping records.

### Our prototype emphasizes:
1. multi-source correlation;
2. entity resolution;
3. intelligence graph;
4. explainable prioritization;
5. hybrid rules + ML;
6. temporal clustering;
7. evidence-linked alert explanations;
8. investigator-centric workflow;
9. human-in-the-loop AI;
10. complete end-to-end prototype.

---

# 10. Competitive Positioning Statement

> Existing anti-doping ecosystems manage operational data, reporting and investigations. Our prototype demonstrates an intelligence-analysis layer that connects fragmented signals, explains why they matter, visualizes relationships and turns prioritized intelligence into evidence-linked investigative workflows.

---

# 11. Do Not Claim

- "better than ADAMS"
- "replaces WADA systems"
- "detects doping with AI"
- "predicts guilt"
- "automatically catches dopers"
- "production-ready whistleblower anonymity"

Use:

- "prototype"
- "investigation prioritization"
- "intelligence lead"
- "analytical signal"
- "decision support"
- "synthetic data"
