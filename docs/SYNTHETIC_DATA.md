# Synthetic Scenario Runtime (G2)

The synthetic scenario runtime turns verified gaps G2/G3 into a deterministic,
reproducible, DB-persisted evaluation system. All data is **synthetic only**
(directive §24/§25) and clearly labelled (`SYN-` external refs). Ground-truth
labels describe the *expected signal pattern* for prototype evaluation only and
never imply guilt.

## Data flow

```
registry.py  ->  generators.py  ->  populate.py  ->  cli.py
 (catalog)       (in-memory set)    (persist + register)   (list/populate/reset)
```

1. **`app/data/registry.py`** — the stable catalog of 7 scenarios (`ScenarioSpec`):
   ref, type, label, description, default seed, ground truth. Refs are stable
   (`SCENARIO_NORMAL_001`, …).
2. **`app/data/generators.py`** — fully deterministic in-memory builders. Every id
   and date derives from a per-key PRNG (`random.Random(f"{seed}:{key}")`), so the
   same `seed + as_of` reproduces the dataset byte-for-byte, while different seeds
   diverge.
3. **`app/data/populate.py`** — persists ORM objects, resolves relationship types by
   name, registers a `SyntheticScenario` row (seed JSON in `extra_refs`), and
   provides an idempotent scoped reset.
4. **`app/data/cli.py`** — `list`, `seed-registry`, `populate`, `reset`.

## Scenario catalog

| ref | type | default seed | expected signal |
|---|---|---|---|
| `SCENARIO_NORMAL_001` | NORMAL | 1100 | no concentrated signal; low load |
| `SCENARIO_ISOLATED_ANOMALY_001` | ISOLATED_ANOMALY | 1201 | strong single-source biological deviation, no corroboration |
| `SCENARIO_TEMPORAL_001` | TEMPORAL | 1302 | temporal cluster + whereabouts failure |
| `SCENARIO_NETWORK_001` | NETWORK | 1403 | dense local network context |
| `SCENARIO_MULTI_SOURCE_001` | MULTI_SOURCE | 1504 | multi-source corroboration |
| `SCENARIO_CORRELATED_ANOMALY_001` | CORRELATED_ANOMALY | 1605 | combined multiple signal categories |
| `SCENARIO_FALSE_POSITIVE_001` | FALSE_POSITIVE | 1706 | strong single signal, stays reviewable (never CRITICAL) |

Each scenario uses a shared deterministic population of 14 athletes, 3 teams,
3 organisations, 3 providers, 4 supplements, 8 support persons and 8 intelligence
sources (including `CONF-HANDLER-01/02` CONFIDENTIAL and `LEO-SHARE` RESTRICTED),
then applies its signature (deviation count, report volume, network edges, etc.).

## CLI

```bash
python -m app.data.cli list
python -m app.data.cli seed-registry [--as-of YYYY-MM-DD]
python -m app.data.cli populate --scenario SCENARIO_ISOLATED_ANOMALY_001 [--seed 42] [--as-of 2026-01-01]
python -m app.data.cli reset
```

`--seed` and `--as-of` freeze reproducibility for a repeatable demo; `--as-of`
defaults to today.

## Engine integration

The runtime feeds the real pipeline (`app/analysis/runner.run_analysis`). All
athletes become subjects (they are not `_clean_domain_tables`-scoped), and the
scenario's target athlete is `SYN-ATH-000`. This exposed and fixed a repository
gap: biological observations now propagate their **baseline deviation** into
`Signal.value` (`app/analysis/repository.py:value_attr`), so the deviation features
and `RULES-005` behave identically for DB-persisted and in-memory subjects.

## Testing

`tests/test_synthetic_scenarios_runtime.py` covers: catalog stability/completeness,
determinism, default-seed stability, target identification, persistence + reset,
and per-scenario pipeline signals (rules triggered, stage scores > 0, level bounds)
using qualitative assertions only — no hard-coded expected scores.
