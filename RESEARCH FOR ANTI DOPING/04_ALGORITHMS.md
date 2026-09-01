# Detailed Detection, Correlation & Risk Algorithms

# 1. Algorithm Architecture

```text
Raw Data
   ↓
Feature Engineering
   ↓
Rule Engine ─────────┐
                     │
Isolation Forest ────┤
                     ↓
Temporal Analysis ───┤
                     ↓
Relationship Analysis┤
                     ↓
Source Assessment ───┤
                     ↓
        Signal Normalization
                     ↓
           Priority Score
                     ↓
             Alert Policy
```

---

# 2. Feature Engineering

For each athlete, construct a rolling feature vector.

## Testing features

- tests_last_30d
- tests_last_90d
- missed_events_last_90d
- adverse_result_count_synthetic
- test_location_count
- test_interval_variance

## Longitudinal features

- marker_count
- mean_marker_deviation
- max_marker_deviation
- deviation_trend
- baseline_shift_signal

## Travel

- travel_count_30d
- distinct_destinations
- rapid_location_changes
- unusual_sequence_signal

## Supplement/provider

- supplement_count
- provider_count
- shared_provider_count
- provider_network_degree

## Intelligence

- report_count
- independent_source_count
- recent_report_count
- source_quality_mean

## Network

- degree
- high-risk_neighbor_count
- shared_entity_count
- cluster_membership

---

# 3. Deterministic Rule Engine

Each rule:

```text
Rule ID
Name
Description
Conditions
Severity
Weight
Evidence fields
Explanation template
Version
```

Example:

## R-001
Repeated testing/whereabouts issue.

Condition:
```text
missed_events_90d >= 2
```

Indicator:
```text
severity = MEDIUM
base_score = 50
```

## R-002
Longitudinal anomaly.

Condition:
```text
max_marker_deviation >= configured_threshold
```

Indicator:
```text
severity = HIGH
```

## R-003
Multi-source corroboration.

Condition:
```text
independent_sources >= 2
AND
reports_within_45d >= 2
```

## R-004
Support-personnel network.

Condition:
```text
same_support_person linked to >= 2
subjects with related indicators
```

## R-005
Shared provider cluster.

Condition:
```text
provider linked to >= 3
subjects
AND
>= 2 subjects have active indicators
```

Rules are not proof of violations.

---

# 4. Isolation Forest

## Why Isolation Forest

It is:
- simple;
- fast;
- unsupervised;
- suitable for a prototype;
- interpretable enough when paired with feature-level explanations.

## Training

Train on synthetic baseline population.

Exclude intentionally injected suspicious cases from the baseline training set.

Parameters:

```text
n_estimators = 200
contamination = 0.05
random_state = 42
```

These are prototype values, not validated operational parameters.

## Output

The model produces an anomaly measure.

Normalize to:

```text
0 = normal relative to model
100 = highly anomalous relative to model
```

Do not call this a probability.

---

# 5. Feature Contribution

Isolation Forest does not natively provide the kind of direct feature attribution required for a simple UI.

Therefore use a secondary explanation strategy:

1. compare current feature vector with population baseline;
2. calculate standardized deviation for each feature;
3. rank deviations;
4. map the top deviations to human-readable labels.

Example:

```text
Top anomalous features:

marker_deviation_score     2.8σ
travel_frequency            2.3σ
network_degree              2.0σ
missed_event_count          1.9σ
```

This is a prototype explanation, not a formal causal explanation.

---

# 6. Temporal Correlation

For each subject:

1. Sort indicators by event date.
2. Create a rolling window.
3. Count distinct indicator categories.
4. Count independent sources.
5. Increase cluster strength when independent categories occur close together.

Example:

```text
Day 1  → intelligence report
Day 8  → travel anomaly
Day 17 → testing issue
Day 30 → provider relationship
```

If the configured window is 45 days:

```text
4 indicator categories
3 source categories
45-day window
```

→ strong temporal cluster.

---

# 7. Cross-Source Correlation

A correlation should require at least two independent signal classes.

Example:

```text
TESTING
+
TRAVEL
+
INTELLIGENCE REPORT
```

is stronger than three records from the same source.

Prototype correlation strength:

```text
independent_categories / configured_max
```

bounded to 0–100.

---

# 8. Network Score

Build a graph.

For each subject:

```text
degree
shared_support_persons
shared_providers
shared_events
high_priority_neighbors
```

Example:

```text
network_score =
  20% normalized_degree
+ 30% high_priority_neighbor_ratio
+ 25% shared_provider_signal
+ 25% shared_support_person_signal
```

Do not infer wrongdoing merely from association.

The relationship is an investigative lead.

---

# 9. Source Reliability

Use an explicit source-assessment model.

Prototype fields:

### Source reliability
How reliable is the source historically?

### Information quality
How specific and corroborated is this individual report?

Use ordinal values such as:

```text
Reliability:
A = highly reliable
B = usually reliable
C = sometimes reliable
D = unreliable
E = untested/unknown

Information quality:
1 = confirmed
2 = probably true
3 = possibly true
4 = doubtful
5 = unknown
```

For the prototype, map these to normalized scores.

Do not claim that this exact grading scheme is the official NADA/WADA scoring system; it is a prototype implementation pattern.

---

# 10. Priority Score

Components:

```text
RuleScore       = 25%
AnomalyScore    = 20%
Correlation     = 20%
Temporal        = 15%
Network         = 10%
SourceQuality   = 10%
```

Formula:

```text
P =
0.25R +
0.20A +
0.20C +
0.15T +
0.10N +
0.10S
```

Where each variable is [0,100].

---

# 11. Alert Policy

```text
0–29   LOW
30–49  MODERATE
50–69  HIGH
70–84  VERY HIGH
85–100 CRITICAL
```

Recommended prototype actions:

LOW:
- store;
- monitor.

MODERATE:
- analyst review.

HIGH:
- prioritized review.

VERY HIGH:
- investigator review recommended.

CRITICAL:
- immediate analyst/investigator review.

The system never automatically opens an enforcement action.

---

# 12. False Positive Handling

A reviewer may select:

- insufficient evidence;
- source unreliable;
- legitimate explanation;
- expected behavior;
- duplicate;
- unrelated correlation;
- model anomaly without corroboration.

Store this feedback.

This becomes future model-evaluation data.

---

# 13. Ground Truth

Create synthetic labels:

```text
NORMAL
KNOWN_PATTERN
SUSPICIOUS_PATTERN
FALSE_POSITIVE
```

The label is for prototype evaluation only.

---

# 14. Evaluation

Calculate:

### Precision
How many flagged records were actually injected as target patterns?

### Recall
How many injected target patterns were detected?

### F1
Balance precision and recall.

### False-positive rate
How often did normal/false-positive records get escalated?

### Ranking quality
Do injected high-priority patterns appear near the top?

The demo should show these metrics in a developer/evaluation screen, not present them as real-world effectiveness.
