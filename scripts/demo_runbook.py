"""End-to-end demo runbook for the LineagePulse submission.

This script is what judges / reviewers can run to see the full pipeline
in action without needing a live DataHub instance. It:

1. Synthesizes a known-failing freshness assertion on the
   ``taxi_trips`` dataset (mirrors the planted scenario in the
   ``nyc-taxi`` sample datapack).
2. Traces a hand-built blast radius that matches the lineage in the
   ``nyc-taxi`` demo: 1 upstream source, 1 downstream aggregate, 1
   ML model in production, 1 dashboard, 1 pipeline.
3. Runs Investigator + Responder.
4. Renders the Slack payload as a Markdown file so it can be inspected
   without a Slack workspace.
5. Renders the DataHub Document body so it can be inspected without
   a writeback.
6. Saves all of this to ``examples/demo_output/``.
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
from lineagepulse.llm import investigate
from lineagepulse.slack import render_blocks


def main() -> int:
    out_dir = REPO_ROOT / "examples" / "demo_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(dry_run=True)

    incident = _synthesize_demo_incident()
    incident.blast_radius = _synthesize_blast_radius(incident.asset.urn)

    print(f"→ Synthesized incident: {incident.id}")
    print(f"  Asset:        {incident.asset.urn}")
    print(f"  Severity:     {incident.severity.value.upper()}")
    print(f"  Owners:       {', '.join(incident.asset.owners)}")
    print(f"  Blast radius: "
          f"{len(incident.blast_radius.upstream)} up / "
          f"{len(incident.blast_radius.downstream)} down / "
          f"{len(incident.blast_radius.affected_ml_models)} ML / "
          f"{len(incident.blast_radius.affected_dashboards)} dashboards")

    # 1. Investigate
    report = investigate(incident, settings)
    incident.root_cause = report.root_cause_hypothesis
    incident.suggested_fix = report.suggested_fix

    # 2. Severity bump
    from lineagepulse.models import IncidentSeverity

    if incident.blast_radius.affected_ml_models:
        incident.severity = IncidentSeverity.CRITICAL

    # 3. Render Slack payload
    blocks = render_blocks(incident, report, settings)

    # 4. Render DataHub Document body
    from lineagepulse.datahub_client import _incident_to_document_body

    doc_body = _incident_to_document_body(incident)
    incident.datahub_document_urn = f"urn:li:document:incident-{incident.id}"

    # 5. Persist artifacts
    artifacts = {
        "incident.json": json.dumps(incident.model_dump(mode="json"), indent=2, default=str),
        "report.json": json.dumps(report.model_dump(mode="json"), indent=2, default=str),
        "slack_blocks.json": json.dumps(blocks, indent=2, default=str),
        "slack_blocks.md": _render_slack_markdown(blocks, incident),
        "datahub_document.md": doc_body,
    }
    for name, content in artifacts.items():
        (out_dir / name).write_text(content)
        print(f"  ✓ wrote {out_dir / name}")

    # 6. Print a friendly summary
    print()
    print("══════════════════════════════════════════════════════════════════")
    print(f"  INCIDENT: {incident.title}")
    print("══════════════════════════════════════════════════════════════════")
    print()
    print("Summary:")
    print(f"  {report.executive_summary}")
    print()
    print("Root cause hypothesis:")
    print(f"  {report.root_cause_hypothesis}")
    print()
    print("Suggested fix:")
    print(f"  {report.suggested_fix}")
    print()
    print(f"DataHub Document: {incident.datahub_document_urn}")
    print(f"Slack channel:    {settings.slack_default_channel}")
    print()
    print("Done. Artifacts in examples/demo_output/")
    return 0


def _render_slack_markdown(blocks: dict, incident) -> str:
    """Render the Slack block-kit payload as Markdown for human inspection."""
    lines: list[str] = []
    lines.append(f"# Slack notification — {incident.title}")
    lines.append("")
    lines.append(f"_Channel: `{incident.asset.domain or 'default'}`_")
    lines.append("")
    for b in blocks.get("blocks", []):
        btype = b.get("type")
        if btype == "header":
            lines.append(f"## {b['text']['text']}")
        elif btype == "section":
            t = b.get("text", {}).get("text", "")
            if t:
                lines.append(t)
            for f in b.get("fields", []) or []:
                lines.append(f"- {f.get('text', '')}")
        elif btype == "context":
            for e in b.get("elements", []) or []:
                lines.append(f"_{e.get('text','')}_")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
