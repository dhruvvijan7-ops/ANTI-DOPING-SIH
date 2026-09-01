"""Command-line driver for the analytics engine.

Runs the full pipeline against the configured database and prints a summary, so the
engine is fully executable without the HTTP API or the web frontend.

Examples:
    python -m app.analysis.cli run
    python -m app.analysis.cli run --limit 20 --threshold HIGH
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import func, select

from app.analysis.contracts import AnalysisConfig
from app.analysis.runner import run_analysis
from app.db.session import SessionLocal
from app.models.analytics import Alert
from app.models.subjects import Athlete


def _run(args: argparse.Namespace) -> int:
    cfg = AnalysisConfig(
        alert_threshold=args.threshold,
        temporal_window_days=args.temporal_window,
        cross_source_window_days=args.cross_source_window,
    )
    with SessionLocal() as db:
        subject_ids = None
        if args.limit and args.limit > 0:
            subject_ids = list(db.scalars(select(Athlete.id).limit(args.limit)).all())
        run = run_analysis(db, config=cfg, subject_ids=subject_ids)
        print(f"Analysis run: {run.id} ({run.status})")
        print(f"  model_version: {run.model_version}  rule_version: {run.rule_version}  feature_version: {run.feature_version}")
        print(f"  result_count: {run.result_count}")
        if run.error:
            print(f"  error: {run.error}")
        if run.status == "COMPLETED":
            alert_count = db.scalar(
                select(func.count(Alert.id)).where(Alert.analysis_run_id == run.id)
            )
            print(f"  alerts: {alert_count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="clean-sport-analysis", description="Anti-doping intelligence analytics engine")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="execute an analysis run")
    run_p.add_argument("--limit", type=int, default=0, help="limit the number of subjects (0 = all)")
    run_p.add_argument("--threshold", type=str, default="HIGH", help="alert threshold level (MODERATE/HIGH/VERY_HIGH/CRITICAL)")
    run_p.add_argument("--temporal-window", type=int, default=45, help="temporal correlation window in days")
    run_p.add_argument("--cross-source-window", type=int, default=90, help="cross-source correlation window in days")
    run_p.set_defaults(handler=_run)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())