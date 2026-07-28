"""Second demo scenario — PII / governance gap on the healthcare dataset.

This shows the agent handling a *different* kind of incident (a missing
PII tag) and proves the agent generalizes across signal types.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
sys.path.insert(0, str(SRC))

from lineagepulse.config import Settings
from lineagepulse.llm import investigate
from lineagepulse.models import (
    AssetRef,
    BlastRadius,
    Incident,
    IncidentKind,
    IncidentSeverity,
)
from lineagepulse.slack import render_blocks


def main() -> int:
    out_dir = REPO_ROOT / "examples" / "demo_output_pii"
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(dry_run=True)

    asset = AssetRef(
        urn="urn:li:dataset:(urn:li:dataPlatform:postgres,healthcare.patients,PROD)",
        type="dataset",
        platform="postgres",
        name="patients",
        owners=["compliance@acme.io", "data-platform@acme.io"],
        domain="Healthcare",
    )
    incident = Incident(
        kind=IncidentKind.GLOSSARY_GAP,
        severity=IncidentSeverity.HIGH,
        title="PII tag missing on patients.email column",
        summary=(
            "The `email` column on `patients` does not have the `PII` glossary term "
            "applied. This is a compliance gap — three downstream reports inherit the "
            "column without masking."
        ),
        asset=asset,
        raw_signal={
            "missing_tag": "PII",
            "column": "email",
            "expected_owners": ["compliance@acme.io"],
        },
    )
    incident.blast_radius = BlastRadius(
        root=asset,
        upstream=[
            AssetRef(urn="urn:li:dataset:(urn:li:dataPlatform:s3,ehr_raw.intake,PROD)", platform="s3", name="ehr_raw_intake"),
        ],
        downstream=[
            AssetRef(urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,reporting.weekly_outreach,PROD)", platform="snowflake", name="weekly_outreach"),
            AssetRef(urn="urn:li:dashboard:(urn:li:dataPlatform:tableau,marketing.engagement,PROD)", platform="tableau", name="Marketing Engagement"),
        ],
    )

    print(f"→ Synthesized incident: {incident.id}")
    report = investigate(incident, settings)
    incident.root_cause = report.root_cause_hypothesis
    incident.suggested_fix = report.suggested_fix

    blocks = render_blocks(incident, report, settings)
    from lineagepulse.datahub_client import _incident_to_document_body

    doc_body = _incident_to_document_body(incident)
    incident.datahub_document_urn = f"urn:li:document:incident-{incident.id}"

    artifacts = {
        "incident.json": json.dumps(incident.model_dump(mode="json"), indent=2, default=str),
        "report.json": json.dumps(report.model_dump(mode="json"), indent=2, default=str),
        "slack_blocks.json": json.dumps(blocks, indent=2, default=str),
        "datahub_document.md": doc_body,
    }
    for name, content in artifacts.items():
        (out_dir / name).write_text(content)
        print(f"  ✓ wrote {out_dir / name}")

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


if __name__ == "__main__":
    sys.exit(main())
