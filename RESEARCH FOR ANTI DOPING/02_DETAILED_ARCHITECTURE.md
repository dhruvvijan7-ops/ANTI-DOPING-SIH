# Detailed System Architecture

## 1. Architectural Style

**Modular monolith + SPA + relational database**

Reason:
- 3-day delivery;
- simple deployment;
- easy debugging;
- Python ML ecosystem;
- clear separation of modules;
- easy future extraction into services.

---

# 2. Logical Layers

## Presentation
React components/pages.

## Application
Use-case services:
- create case;
- ingest intelligence;
- run analysis;
- triage alert;
- generate report.

## Domain
Core entities and business rules.

## Analytics
- rule engine;
- feature engineering;
- anomaly detection;
- correlation;
- scoring.

## Persistence
SQLAlchemy repositories.

## Infrastructure
- database;
- file storage;
- authentication;
- AI provider;
- logging.

---

# 3. Backend Modules

```text
app/
├── main.py
├── config/
├── auth/
├── users/
├── athletes/
├── intelligence/
├── sources/
├── entities/
├── analysis/
│   ├── rules/
│   ├── features/
│   ├── anomaly/
│   ├── correlation/
│   └── scoring/
├── alerts/
├── investigations/
├── evidence/
├── relationships/
├── reports/
├── audit/
├── resources/
└── common/
```

---

# 4. Frontend Modules

```text
src/
├── app/
├── routes/
├── layouts/
├── components/
│   ├── ui/
│   ├── charts/
│   ├── intelligence/
│   ├── investigations/
│   ├── graph/
│   └── common/
├── features/
│   ├── auth/
│   ├── dashboard/
│   ├── athletes/
│   ├── alerts/
│   ├── investigations/
│   ├── intelligence/
│   └── reports/
├── services/
├── hooks/
├── stores/
├── types/
└── lib/
```

---

# 5. API Architecture

Use REST JSON.

All protected routes require authentication.

Example response:

```json
{
  "data": {},
  "meta": {
    "request_id": "req_123"
  }
}
```

Errors:

```json
{
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "Investigation case does not exist",
    "request_id": "req_123"
  }
}
```

---

# 6. API Contract

## Authentication

POST `/api/v1/auth/login`

Request:
```json
{
  "username": "investigator",
  "password": "demo-password"
}
```

Response:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "USR-001",
    "role": "INVESTIGATOR"
  }
}
```

## Dashboard

GET `/api/v1/dashboard/summary`

Returns:
- athlete count;
- intelligence count;
- alert count;
- open cases;
- risk distribution;
- recent alerts.

## Athletes

GET `/api/v1/athletes?search=&risk=&sport=`

GET `/api/v1/athletes/{id}`

GET `/api/v1/athletes/{id}/timeline`

GET `/api/v1/athletes/{id}/relationships`

GET `/api/v1/athletes/{id}/alerts`

## Intelligence

POST `/api/v1/intelligence/import`

POST `/api/v1/intelligence`

GET `/api/v1/intelligence`

GET `/api/v1/intelligence/{id}`

POST `/api/v1/intelligence/{id}/assess`

## Analysis

POST `/api/v1/analysis/run`

Request:
```json
{
  "scope": "ALL",
  "model_version": "iforest-v1",
  "rule_set": "default-v1"
}
```

GET `/api/v1/analysis/runs/{id}`

GET `/api/v1/analysis/runs/{id}/results`

## Alerts

GET `/api/v1/alerts`

GET `/api/v1/alerts/{id}`

POST `/api/v1/alerts/{id}/review`

POST `/api/v1/alerts/{id}/convert-to-case`

## Cases

POST `/api/v1/investigations`

GET `/api/v1/investigations`

GET `/api/v1/investigations/{id}`

PATCH `/api/v1/investigations/{id}`

POST `/api/v1/investigations/{id}/assign`

POST `/api/v1/investigations/{id}/evidence`

POST `/api/v1/investigations/{id}/notes`

POST `/api/v1/investigations/{id}/tasks`

POST `/api/v1/investigations/{id}/actions`

GET `/api/v1/investigations/{id}/timeline`

GET `/api/v1/investigations/{id}/graph`

## Reports

POST `/api/v1/investigations/{id}/report`

GET `/api/v1/investigations/{id}/report`

## Audit

GET `/api/v1/audit?case_id=`

---

# 7. Deployment

Docker Compose:

```yaml
services:
  frontend:
  backend:
  postgres:
```

Optional:
- local object storage if file uploads are needed.

---

# 8. Future Production Evolution

Prototype:
**modular monolith**

Future:
```text
API Gateway
   |
Auth
   |
Intelligence Service
Analytics Service
Case Service
Reporting Service
Notification Service
   |
Event Bus
   |
PostgreSQL + analytical store + object store + search
```

Do not implement this during the 3-day prototype.
