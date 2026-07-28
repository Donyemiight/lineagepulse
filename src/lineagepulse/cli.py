"""Command-line interface for LineagePulse."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from lineagepulse import agent
from lineagepulse.config import Settings, get_settings
from lineagepulse.datahub_client import DataHubClient
from lineagepulse.models import (
    AssetRef,
    BlastRadius,
    Incident,
    IncidentKind,
    IncidentSeverity,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lineagepulse",
        description="LineagePulse — DataHub Agent Hackathon submission",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run the agent once (default) or daemon")
    p_run.add_argument("--once", action="store_true", help="Run a single cycle (default)")
    p_run.add_argument("--daemon", action="store_true", help="Run continuously, polling")
    p_run.add_argument("--dry-run", action="store_true", help="Do not write to DataHub or Slack")

    p_demo = sub.add_parser("demo", help="Run a synthetic incident through the full pipeline")
    p_demo.add_argument(
        "--out",
        type=Path,
        default=Path("examples/last_demo_run.json"),
        help="Where to write the JSON dump of the demo run",
    )

    p_inspect = sub.add_parser("inspect", help="Inspect a URN: lineage + schema")
    p_inspect.add_argument("urn")
    p_inspect.add_argument("--depth", type=int, default=3)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    settings = get_settings()

    if args.cmd == "run":
        if args.dry_run:
            settings = Settings(**{**settings.model_dump(), "dry_run": True})
        if args.daemon:
            agent.run_daemon(settings)
        else:
            agent.run_once(settings)
        return 0

    if args.cmd == "demo":
        return _run_demo(settings, args.out)

    if args.cmd == "inspect":
        return _inspect(settings, args.urn, args.depth)

    return 1


# ---------------------------------------------------------------- demo
def _run_demo(settings: Settings, out_path: Path) -> int:
    """Simulate a known-failing assertion and watch the agent respond.

    This is the deterministic path used by ``examples/`` and the smoke
    test. It does NOT require a live DataHub instance.
    """
    demo_incident = _synthesize_demo_incident()
    client = DataHubClient(settings)
    blast = _synthesize_blast_radius(demo_incident.asset.urn)
    demo_incident.blast_radius = blast

    from lineagepulse.llm import investigate

    report = investigate(demo_incident, settings)
    demo_incident.root_cause = report.root_cause_hypothesis
    demo_incident.suggested_fix = report.suggested_fix
    demo_incident._report = report  # type: ignore[attr-defined]

    if not settings.dry_run:
        demo_incident = agent.respond_to_incident(demo_incident, client, settings)

    payload = {
        "demo": True,
        "settings_dry_run": settings.dry_run,
        "incident": demo_incident.model_dump(mode="json"),
        "report": report.model_dump(mode="json"),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"Demo run written to {out_path}")
    print()
    print("── Executive summary ───────────────────────────────────────")
    print(report.executive_summary)
    print()
    print("── Root cause hypothesis ───────────────────────────────────")
    print(report.root_cause_hypothesis)
    print()
    print("── Suggested fix ──────────────────────────────────────────")
    print(report.suggested_fix)
    return 0


def _synthesize_demo_incident() -> Incident:
    asset = AssetRef(
        urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,demo.warehouse.taxi_trips,PROD)",
        type="dataset",
        platform="snowflake",
        name="taxi_trips",
        owners=["ademidun@acme.io", "data-platform@acme.io"],
        domain="Mobility",
    )
    return Incident(
        kind=IncidentKind.FRESHNESS_VIOLATION,
        severity=IncidentSeverity.HIGH,
        title="Freshness violation on taxi_trips (3h 12m stale)",
        summary=(
            "taxi_trips has not received new rows in 3h 12m. The freshness "
            "assertion expects rows at most 1h apart. Downstream ML model "
            "demand_forecaster is now training on stale data."
        ),
        asset=asset,
        raw_signal={
            "assertion_urn": "urn:li:assertion:taxi-freshness",
            "expected_max_age_minutes": 60,
            "observed_age_minutes": 192,
        },
    )


def _synthesize_blast_radius(root_urn: str) -> BlastRadius:
    root = AssetRef(
        urn=root_urn,
        type="dataset",
        platform="snowflake",
        name="taxi_trips",
        owners=["ademidun@acme.io", "data-platform@acme.io"],
        domain="Mobility",
    )
    return BlastRadius(
        root=root,
        upstream=[
            AssetRef(urn="urn:li:dataset:(urn:li:dataPlatform:s3,raw.taxi.zones,PROD)", type="dataset", platform="s3", name="raw_taxi_zones"),
        ],
        downstream=[
            AssetRef(urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,demo.warehouse.daily_revenue,PROD)", type="dataset", platform="snowflake", name="daily_revenue"),
        ],
        affected_ml_models=[
            AssetRef(urn="urn:li:mlModel:(urn:li:dataPlatform:mlflow,demand_forecaster,PROD)", type="mlModel", platform="mlflow", name="demand_forecaster", owners=["ml-team@acme.io"]),
        ],
        affected_dashboards=[
            AssetRef(urn="urn:li:dashboard:(urn:li:dataPlatform:looker,daily_ops,PROD)", type="dashboard", platform="looker", name="Daily Ops", owners=["ops@acme.io"]),
        ],
        affected_pipelines=[
            AssetRef(urn="urn:li:dataJob:(urn:li:dataPlatform:airflow,taxi_ingest,taxi_load)", type="dataJob", platform="airflow", name="taxi_load"),
        ],
    )


# -------------------------------------------------------------- inspect
def _inspect(settings: Settings, urn: str, depth: int) -> int:
    client = DataHubClient(settings)
    asset = client.get_asset(urn)
    blast = client.get_lineage(urn, max_depth=depth)
    print(json.dumps(
        {
            "asset": asset.model_dump() if asset else None,
            "blast_radius": blast.model_dump(),
        },
        indent=2,
        default=str,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
