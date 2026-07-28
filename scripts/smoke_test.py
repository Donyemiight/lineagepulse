"""End-to-end smoke test for LineagePulse.

Runs the agent in DRY_RUN mode against a synthesized incident and
asserts that the full pipeline (investigation → report → Slack payload
→ writeback) executes without errors and produces valid output.

This is the test that runs in CI and that the demo runbook produces a
JSON record for. No live DataHub is required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
sys.path.insert(0, str(SRC))

from lineagepulse.cli import _synthesize_blast_radius, _synthesize_demo_incident
from lineagepulse.config import Settings
from lineagepulse.datahub_client import DataHubClient
from lineagepulse.llm import investigate


def main() -> int:
    settings = Settings(dry_run=True)
    if not settings.has_llm_credentials():
        print("ℹ No LLM credentials — using heuristic report path")

    incident = _synthesize_demo_incident()
    incident.blast_radius = _synthesize_blast_radius(incident.asset.urn)
    print(f"→ Synthesized incident: {incident.id[:8]} on {incident.asset.name}")

    # 1. Investigation (LLM or heuristic)
    report = investigate(incident, settings)
    incident.root_cause = report.root_cause_hypothesis
    incident.suggested_fix = report.suggested_fix
    incident._report = report  # type: ignore[attr-defined]
    assert report.title, "report.title must be set"
    assert report.executive_summary, "report.executive_summary must be set"
    print("✓ Investigation produced a valid IncidentReport")

    # 2. Slack render (in dry-run mode, just builds the payload)
    from lineagepulse.slack import render_blocks

    blocks = render_blocks(incident, report, settings)
    assert blocks.get("blocks"), "Slack blocks must be non-empty"
    print(f"✓ Slack payload has {len(blocks['blocks'])} blocks")

    # 3. DataHub writeback (in dry-run mode, this is a no-op)
    client = DataHubClient(settings)
    doc_urn = client.write_incident_document(incident)
    if settings.dry_run:
        assert doc_urn is None, "dry-run should not write"
        print("✓ DRY_RUN: no DataHub write attempted (correct)")
    else:
        print(f"✓ Wrote DataHub document: {doc_urn}")

    # 4. Severity bump from ML lineage
    from lineagepulse.models import IncidentSeverity

    if incident.blast_radius and incident.blast_radius.affected_ml_models:
        incident.severity = IncidentSeverity.CRITICAL
        print(f"✓ Bumped severity to CRITICAL ({len(incident.blast_radius.affected_ml_models)} ML model(s) in blast radius)")

    # 5. Persist the run for the examples/ folder
    out = REPO_ROOT / "examples" / "smoke_test_output.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "incident": incident.model_dump(mode="json"),
        "report": report.model_dump(mode="json"),
        "slack_blocks_count": len(blocks["blocks"]),
    }, indent=2, default=str))
    print(f"✓ Wrote {out}")

    print()
    print("── Executive summary ───────────────────────────────────────")
    print(report.executive_summary)
    print()
    print("── Root cause hypothesis ───────────────────────────────────")
    print(report.root_cause_hypothesis)
    print()
    print("── Suggested fix ──────────────────────────────────────────")
    print(report.suggested_fix)
    print()
    print("✅ Smoke test PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
