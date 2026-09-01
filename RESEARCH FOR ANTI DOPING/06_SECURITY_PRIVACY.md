# Security, Privacy & Trust Specification

## 1. Domain risk

This platform may process highly sensitive information about athletes, medical information, investigation records and confidential sources.

NADA India states that it processes personal information for anti-doping activities and that its processing is governed by applicable anti-doping privacy standards and national law. WADA's privacy standard exists specifically because anti-doping programs can involve substantial personal information.

Therefore privacy is a core product requirement, not an optional feature.

---

# 2. Prototype data rule

Use only:
- synthetic athletes;
- synthetic events;
- synthetic reports;
- fictional organizations;
- fictional providers;
- fictional case records.

Do not import:
- real athlete medical records;
- real financial transactions;
- real confidential-source identities;
- leaked data;
- scraped private information.

---

# 3. Threat Model

## Threat 1 — Unauthorized access
Mitigation:
- authentication;
- RBAC;
- backend authorization.

## Threat 2 — Privilege escalation
Mitigation:
- server-side permission checks;
- no trust in frontend role values.

## Threat 3 — Data leakage
Mitigation:
- synthetic data;
- classification labels;
- controlled API responses;
- no sensitive logging.

## Threat 4 — Evidence tampering
Mitigation:
- audit events;
- file hash;
- immutable evidence metadata where feasible.

## Threat 5 — Model manipulation
Mitigation:
- version models;
- version rules;
- log analysis runs;
- protect configuration.

## Threat 6 — AI hallucination
Mitigation:
- AI only receives retrieved case records;
- structured prompt;
- no autonomous action;
- show source references.

## Threat 7 — Correlation bias
Mitigation:
- show relationship evidence;
- do not infer wrongdoing by association;
- require human review.

## Threat 8 — False positive
Mitigation:
- human triage;
- false-positive outcome;
- feedback tracking.

---

# 4. RBAC Matrix

| Capability | Admin | Investigator | Analyst | Viewer |
|---|---:|---:|---:|---:|
| Dashboard | ✓ | ✓ | ✓ | ✓ |
| Athlete view | ✓ | ✓ | ✓ | ✓ |
| Intelligence intake | ✓ | ✓ | ✓ | - |
| Run analysis | ✓ | ✓ | ✓ | - |
| Review alerts | ✓ | ✓ | ✓ | ✓ |
| Create case | ✓ | ✓ | ✓ | - |
| Modify case | ✓ | ✓ | limited | - |
| Add evidence | ✓ | ✓ | ✓ | - |
| Assign cases | ✓ | ✓ | - | - |
| Configure rules | ✓ | - | - | - |
| Manage users | ✓ | - | - | - |
| Audit logs | ✓ | authorized | authorized | read-only |

---

# 5. Confidentiality Classification

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

The prototype must enforce at least role-based access to restricted records.

---

# 6. Audit Requirements

Record:
- who;
- what;
- when;
- object;
- action;
- result.

Never store:
- plaintext passwords;
- secret keys;
- full authentication tokens.

---

# 7. AI Safety Rules

The assistant must not:
- accuse;
- sanction;
- fabricate;
- infer guilt;
- reveal restricted information to unauthorized users.

It may:
- summarize;
- compare;
- explain;
- retrieve;
- suggest investigative questions.

---

# 8. Future Production Requirements

A production system would require:
- formal privacy impact assessment;
- legal review;
- data retention schedules;
- data subject rights processes where applicable;
- encryption at rest/in transit;
- HSM/key-management strategy where required;
- security monitoring;
- penetration testing;
- secure SDLC;
- disaster recovery;
- incident response;
- independent audit;
- controlled cross-border data transfers;
- confidential-source operational procedures.
