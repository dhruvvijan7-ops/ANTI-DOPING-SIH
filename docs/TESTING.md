# Testing

**Last updated:** 2026-09-01

Testing strategy for CleanSport Intelligence. This documents both what exists today
and the full intended coverage; unimplemented areas are marked **(planned)**.

---

## 1. Current coverage — backend

Run from `backend/`:

```bash
pytest
```

Existing suites:

| File | Covers |
|---|---|
| `tests/conftest.py` | Test DB provisioning (migrations + seed), fixtures, client |
| `tests/test_auth.py` | Login, logout, current-user, password hashing, token behavior |
| `tests/test_authz.py` | RBAC role/permission enforcement (403s, allowed access) |

Note: `conftest.py` test-DB URL currently defaults to `localhost:5432`; align with
the configured host port (`54320`) or an env override before running.

---

## 2. Planned coverage

### 2.1 Backend API

- All endpoints: status codes, validation errors, authentication required.
- Authorization: each role's allowed/denied matrix across routes.
- Business logic services (auth, audit; later intelligence, alerts, investigations,
  reporting, AI).

### 2.2 Intelligence engine

| Module | Tests |
|---|---|
| Rules | Versioned definitions, deterministic firing, structured results |
| Anomaly detection | Isolation Forest pipeline, normalized score bounds, feature-level explanation |
| Temporal correlation | Rolling-window (default 45d) clustering and patterns |
| Cross-source correlation | Signal combination from multiple categories; diversity ≠ proof |
| Network/graph | Degree/weighted-degree/diversity metrics; graph endpoint payloads |
| Entity resolution | Deterministic + fuzzy matching; never auto-merge uncertain (spec §16) |
| Priority scoring | Formula `P=0.25R+0.20A+0.20C+0.15T+0.10N+0.10S`, decomposition, level mapping |

### 2.3 Frontend (planned)

- Components, pages, forms, state management, API interactions.

### 2.4 End-to-end (planned)

Complete flow against seeded synthetic data:

```text
Synthetic Data
  ↓ Processing
Signal
  ↓
Alert
  ↓
Investigation
  ↓
Evidence
  ↓
Report
```

### 2.5 Analytical validation (STAGE J)

- Nine known synthetic scenarios must separate cleanly on priority/alerts
  (see `07_TESTING_AND_DATA.md`).

---

## 3. Test principles

- **Deterministic:** intelligence-engine tests use fixed seeds and fixed synthetic
  inputs; no flaky randomness.
- **Isolated:** tests run against `clean_sport_test`, rebuilt by migrations + seed.
- **Boundary-aware:** tests assert the investigative vocabulary — no test asserts a
  "guilt" output; anomaly tests assert "unusual relative to reference population".
- **Explainable:** alert tests assert that every generated alert has a
  contribute-signals explanation path (see `ARCHITECTURE.md` §4).
- **CI:** the CI workflow runs lint/type-check/tests/build as each stage enables them.