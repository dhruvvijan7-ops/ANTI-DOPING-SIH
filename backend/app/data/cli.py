"""Command-line interface for the synthetic scenario runtime (G2).

Usage:
    python -m app.data.cli list
    python -m app.data.cli reset
    python -m app.data.cli seed-registry [--as-of YYYY-MM-DD]
    python -m app.data.cli populate --scenario SCENARIO_ISOLATED_ANOMALY_001 [--seed 42] [--as-of 2026-01-01]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from app.db.session import SessionLocal
from app.data.populate import (
    list_scenarios,
    populate,
    reset_synthetic,
    seed_registry,
)
from app.data.registry import BY_REF
from app.models.scenarios import SyntheticScenario


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.data.cli", description="Synthetic scenario runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list the scenario registry with ground-truth labels")
    sub.add_parser("reset", help="truncate the synthetic domain tables")

    seed_registry_p = sub.add_parser("seed-registry", help="persist registry metadata rows only")
    seed_registry_p.add_argument("--as-of", type=date.fromisoformat, default=None)

    populate_p = sub.add_parser("populate", help="generate and persist one scenario")
    populate_p.add_argument(
        "--scenario", required=True, choices=sorted(BY_REF), help="scenario reference"
    )
    populate_p.add_argument("--seed", type=int, default=None, help="override default seed")
    populate_p.add_argument("--as-of", type=date.fromisoformat, default=None, help="reference date")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _arg_parser().parse_args(argv)
    with SessionLocal() as db:
        if args.command == "list":
            print(json.dumps(list_scenarios(), indent=2))
            return 0
        if args.command == "reset":
            reset_synthetic(db)
            print("synthetic domain reset")
            return 0
        if args.command == "seed-registry":
            seed_registry(db, as_of=args.as_of)
            print(f"registry metadata persisted ({len(BY_REF)} scenarios)")
            return 0
        if args.command == "populate":
            row = populate(db, args.scenario, seed=args.seed, as_of=args.as_of, reset_first=True)
            _print_row(row)
            return 0
        print(f"unknown command: {args.command}", file=sys.stderr)
        return 2


def _print_row(row: SyntheticScenario) -> None:
    payload = json.loads(row.extra_refs or "{}")
    print(
        json.dumps(
            {
                "scenario_ref": row.scenario_ref,
                "scenario_type": row.scenario_type,
                "subject_id": str(row.subject_id) if row.subject_id else None,
                "params": payload,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())