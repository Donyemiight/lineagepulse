"""The LineagePulse agent.

Three cooperating sub-agents, each with a single responsibility:

1. ``Detector`` — poll DataHub for failing assertions and schema events.
2. ``Investigator`` — for each incident, walk the lineage blast radius
   and ask the LLM to author a root-cause report.
3. ``Responder`` — write the incident document back to DataHub, then
   notify the owners via Slack.

The top-level ``handle_incident`` orchestrates all three. ``run_once``
is a single iteration; ``run_daemon`` is the long-running loop.
"""

from __future__ import annotations

import logging
import time

from rich.console import Console
from rich.table import Table

from lineagepulse import slack
from lineagepulse.config import Settings, get_settings
from lineagepulse.datahub_client import DataHubClient
from lineagepulse.llm import investigate
from lineagepulse.models import (
    Incident,
    IncidentReport,
    IncidentStatus,
)

logger = logging.getLogger(__name__)
console = Console()


# ============================================================== Detector
def detect_incidents(
    client: DataHubClient,
    settings: Settings,
) -> list[Incident]:
    """Pull currently-failing signals from DataHub."""
    logger.info("Detector: polling for failing assertions…")
    incidents = client.fetch_failing_assertions()
    logger.info("Detector: found %d incident(s)", len(incidents))
    return incidents


# =========================================================== Investigator
def investigate_incident(
    incident: Incident,
    client: DataHubClient,
    settings: Settings,
) -> Incident:
    """Attach a blast radius and an LLM-authored report to the incident."""
    incident.status = IncidentStatus.INVESTIGATING
    logger.info("Investigator: tracing lineage for %s", incident.asset.urn)

    blast = client.get_lineage(
        incident.asset.urn,
        direction="downstream",
        max_depth=settings.lineage_depth,
    )
    # If the seed incident has no asset metadata, fill it from the graph
    if incident.asset.owners == [] and blast.root.owners:
        incident.asset.owners = blast.root.owners
    if incident.asset.name is None:
        incident.asset.name = blast.root.name
    if incident.asset.platform is None:
        incident.asset.platform = blast.root.platform
    if incident.asset.domain is None:
        incident.asset.domain = blast.root.domain

    incident.blast_radius = blast

    # ML-aware severity bump
    if blast.affected_ml_models:
        from lineagepulse.models import IncidentSeverity

        incident.severity = IncidentSeverity.CRITICAL
        logger.info(
            "Investigator: %d ML model(s) in blast radius — severity CRITICAL",
            len(blast.affected_ml_models),
        )

    report = investigate(incident, settings)
    incident.root_cause = report.root_cause_hypothesis
    incident.suggested_fix = report.suggested_fix
    incident._report = report  # type: ignore[attr-defined]
    return incident


# ============================================================= Responder
def respond_to_incident(
    incident: Incident,
    client: DataHubClient,
    settings: Settings,
) -> Incident:
    """Write back to DataHub, then notify Slack."""
    report: IncidentReport = getattr(incident, "_report", None) or _bare_report(incident)

    # 1. Write structured incident document back to DataHub
    doc_urn = client.write_incident_document(incident)
    if doc_urn:
        logger.info("Responder: wrote document %s", doc_urn)

    # 2. Notify Slack
    if incident.asset.owners:
        ts = slack.post_incident(incident, report, settings)
        if ts:
            incident.slack_message_ts = ts
            incident.notified_owners = list(incident.asset.owners)
            incident.status = IncidentStatus.NOTIFIED
            logger.info(
                "Responder: notified %d owner(s) on Slack",
                len(incident.asset.owners),
            )
    else:
        logger.info("Responder: no owners found — Slack notification skipped")

    return incident


# ============================================================ Orchestrator
def handle_incident(
    incident: Incident,
    client: DataHubClient,
    settings: Settings,
) -> Incident:
    """End-to-end: investigate → respond."""
    incident = investigate_incident(incident, client, settings)
    incident = respond_to_incident(incident, client, settings)
    return incident


def run_once(settings: Settings | None = None) -> list[Incident]:
    """One iteration of the agent loop."""
    s = settings or get_settings()
    client = DataHubClient(s)
    incidents = detect_incidents(client, s)
    handled: list[Incident] = []
    for inc in incidents:
        try:
            handled.append(handle_incident(inc, client, s))
        except Exception:
            logger.exception("handle_incident failed")
    return handled


def run_daemon(settings: Settings | None = None) -> None:
    """Long-running loop with polling."""
    s = settings or get_settings()
    logger.info("LineagePulse daemon starting (poll every %ss)…", s.poll_interval_seconds)
    while True:
        try:
            handled = run_once(s)
            _print_summary(handled)
        except Exception:
            logger.exception("run_once failed")
        time.sleep(s.poll_interval_seconds)


# ----------------------------------------------------------------- display
def _print_summary(handled: list[Incident]) -> None:
    if not handled:
        console.print("[green]✓[/green] no new incidents")
        return
    table = Table(title="LineagePulse — incidents handled", show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Severity", style="bold")
    table.add_column("Asset")
    table.add_column("ML?", justify="center")
    table.add_column("Slack?", justify="center")
    table.add_column("Doc?", justify="center")
    for inc in handled:
        ml = (
            f"[red]{len(inc.blast_radius.affected_ml_models)}[/red]"
            if inc.blast_radius and inc.blast_radius.affected_ml_models
            else "—"
        )
        slack_cell = "[green]✓[/green]" if inc.slack_message_ts else "[grey]—[/grey]"
        doc_cell = "[green]✓[/green]" if inc.datahub_document_urn else "[grey]—[/grey]"
        sev_color = {
            "low": "blue",
            "medium": "yellow",
            "high": "red",
            "critical": "bold red",
        }.get(inc.severity.value, "white")
        table.add_row(
            inc.id[:8],
            f"[{sev_color}]{inc.severity.value.upper()}[/{sev_color}]",
            inc.asset.name or inc.asset.urn,
            ml,
            slack_cell,
            doc_cell,
        )
    console.print(table)


def _bare_report(incident: Incident) -> IncidentReport:
    return IncidentReport(
        title=incident.title,
        executive_summary=incident.summary,
        root_cause_hypothesis=incident.root_cause or "Pending investigation.",
        suggested_fix=incident.suggested_fix or "Re-run the upstream pipeline.",
        blast_radius_summary="",
        severity_rationale=incident.severity.value,
        recommended_actions=[],
    )
