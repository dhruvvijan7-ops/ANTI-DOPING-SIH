# Database Schema Specification

## 1. users

- id UUID
- username
- email
- password_hash
- role_id
- status
- created_at
- updated_at
- last_login_at

## 2. roles

- id
- name
- description

## 3. permissions

- id
- key
- description

## 4. role_permissions

- role_id
- permission_id

## 5. athletes

- id
- external_ref
- first_name
- last_name
- date_of_birth
- nationality
- sport
- discipline
- team_id
- status
- created_at
- updated_at

## 6. support_personnel

- id
- name
- role
- organization
- country
- status

## 7. teams

- id
- name
- sport
- federation
- country

## 8. organizations

- id
- name
- type
- country

## 9. sources

- id
- name
- source_type
- reliability_default
- confidentiality
- active

Source types:
- TESTING
- ABP
- WHEREABOUTS
- MEDICAL
- TUE
- REPORT
- OSINT
- TRAVEL
- FINANCIAL
- FEDERATION
- LAW_ENFORCEMENT
- OTHER

## 10. intelligence_reports

- id
- source_id
- external_ref
- subject_type
- subject_id
- title
- description
- report_date
- ingestion_date
- reliability
- information_quality
- confidentiality
- status
- created_by

## 11. tests

- id
- athlete_id
- test_date
- test_type
- location
- result_classification
- laboratory_ref
- source_id

Use synthetic classifications; do not imply real laboratory findings.

## 12. biological_observations

- id
- athlete_id
- observation_date
- marker
- value
- unit
- baseline_deviation
- source_id

## 13. whereabouts_events

- id
- athlete_id
- event_date
- event_type
- expected_location
- observed_location
- status
- source_id

## 14. medical_events

- id
- athlete_id
- event_date
- event_type
- provider_id
- metadata_classification
- source_id

## 15. supplements

- id
- name
- provider_id
- category
- status

## 16. travel_events

- id
- athlete_id
- event_date
- origin
- destination
- event_type
- source_id

## 17. relationships

- id
- from_entity_type
- from_entity_id
- relationship_type
- to_entity_type
- to_entity_id
- start_date
- end_date
- confidence
- source_id

## 18. indicators

- id
- subject_type
- subject_id
- indicator_type
- severity
- score
- explanation
- rule_version
- evidence_refs
- created_at

## 19. analysis_runs

- id
- run_type
- model_version
- rule_set_version
- parameters_json
- started_at
- completed_at
- status

## 20. anomaly_results

- id
- analysis_run_id
- subject_type
- subject_id
- raw_score
- normalized_score
- feature_snapshot

## 21. alerts

- id
- alert_ref
- subject_type
- subject_id
- priority_score
- priority_level
- status
- explanation
- analysis_run_id
- created_at
- reviewed_at
- reviewed_by

## 22. intelligence_clusters

- id
- cluster_type
- subject_id
- time_start
- time_end
- strength
- explanation

## 23. investigations

- id
- case_ref
- title
- priority
- status
- lead_subject_id
- assigned_to
- opened_at
- due_at
- closed_at
- outcome

## 24. evidence

- id
- case_id
- evidence_type
- title
- description
- source_id
- collected_at
- confidentiality
- file_path
- file_hash
- created_by
- created_at

## 25. investigation_notes

- id
- case_id
- author_id
- note_type
- content
- created_at
- updated_at

## 26. investigation_tasks

- id
- case_id
- assigned_to
- title
- description
- priority
- due_at
- status
- created_at
- completed_at

## 27. investigation_actions

- id
- case_id
- actor_id
- action_type
- description
- created_at

## 28. case_outcomes

- id
- case_id
- outcome
- rationale
- decided_by
- decided_at

## 29. audit_events

- id
- actor_id
- action
- entity_type
- entity_id
- timestamp
- metadata_json

## 30. model_versions

- id
- name
- version
- algorithm
- configuration
- training_dataset
- created_at
- active

## 31. rule_versions

- id
- rule_id
- version
- expression
- severity
- weight
- active
- created_at

---

# 2. Relationships

```text
Athlete
 ├── Tests
 ├── Biological Observations
 ├── Whereabouts
 ├── Medical Events
 ├── Travel
 ├── Intelligence Reports
 ├── Alerts
 ├── Investigations
 └── Relationships

Investigation
 ├── Intelligence Reports
 ├── Evidence
 ├── Notes
 ├── Tasks
 ├── Actions
 ├── Alerts
 └── Outcome
```

---

# 3. Indexes

Create indexes on:
- athlete external_ref
- athlete name
- test athlete/date
- intelligence source/date
- intelligence subject
- alerts priority/status
- investigations status/assignee
- relationships from/to entity
- audit entity/timestamp

---

# 4. Prototype data volumes

The synthetic dataset should be large enough to demonstrate search and analysis but small enough to execute quickly.

Target:
500 athletes,
5,000 tests,
3,000 travel events,
2,000 intelligence reports,
1,500 relationships,
50 cases.

---

# 5. Data integrity

Foreign keys should be enforced.

Do not hard-delete evidence or audit events in normal workflows.

Use status/deactivation where possible.
