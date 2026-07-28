"""Minimal web UI for LineagePulse.

A FastAPI app that exposes:

- ``GET /`` — landing page
- ``GET /demo`` — run the synthetic demo incident
- ``GET /demo/pii`` — run the PII compliance scenario
- ``GET /slack`` — render the Slack block kit
- ``GET /document`` — render the DataHub Document
- ``GET /health`` — health check (for Render)
- ``GET /report`` — full JSON report

Designed to run in DRY_RUN mode in the cloud (no DataHub / no Slack
credentials needed). The same routes are useful for local development
when env vars are set.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from lineagepulse.cli import _synthesize_blast_radius, _synthesize_demo_incident
from lineagepulse.config import Settings
from lineagepulse.datahub_client import DataHubClient, _incident_to_document_body
from lineagepulse.llm import investigate
from lineagepulse.models import Incident, IncidentSeverity
from lineagepulse.slack import render_blocks

app = FastAPI(
    title="LineagePulse",
    description="The first responder your data graph actually wakes up to.",
    version="0.1.0",
)


# ---------------------------------------------------------------- landing
INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>LineagePulse · DataHub Agent Hackathon</title>
<style>
  :root {
    --bg: #0f172a;
    --fg: #f8fafc;
    --muted: #64748b;
    --accent: #38bdf8;
    --danger: #ef4444;
    --warn: #fbbf24;
    --good: #22c55e;
    --card: #1e293b;
    --line: #334155;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--fg); font-family: -apple-system, "SF Pro Display", "Inter", sans-serif; line-height: 1.55; }
  .wrap { max-width: 920px; margin: 0 auto; padding: 64px 32px; }
  h1 { font-size: 64px; line-height: 1.1; margin: 0 0 8px; color: var(--accent); font-weight: 800; letter-spacing: -0.03em; }
  .sub { font-size: 20px; color: var(--muted); margin-bottom: 48px; }
  .accent { width: 120px; height: 4px; background: var(--accent); margin: 24px 0; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin: 32px 0; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 20px; }
  .card h3 { margin: 0 0 8px; font-size: 18px; }
  .card p { margin: 0 0 12px; color: var(--muted); font-size: 14px; }
  a.btn { display: inline-block; padding: 10px 18px; background: var(--accent); color: var(--bg); border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; }
  a.btn:hover { filter: brightness(1.1); }
  a.btn.outline { background: transparent; border: 1px solid var(--accent); color: var(--accent); }
  pre { background: #020617; border: 1px solid var(--line); border-radius: 8px; padding: 16px; overflow-x: auto; font-size: 13px; }
  code { font-family: "SF Mono", "JetBrains Mono", Menlo, monospace; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; background: var(--line); color: var(--fg); margin-right: 6px; }
  .badge.good { background: var(--good); color: #022c11; }
  .badge.warn { background: var(--warn); color: #422006; }
  .badge.danger { background: var(--danger); color: #fff; }
  ul.checks { list-style: none; padding: 0; }
  ul.checks li { padding: 6px 0; padding-left: 24px; position: relative; }
  ul.checks li::before { content: "✓"; position: absolute; left: 0; color: var(--good); font-weight: bold; }
  footer { color: var(--muted); font-size: 13px; margin-top: 64px; padding-top: 24px; border-top: 1px solid var(--line); }
  footer a { color: var(--accent); }
</style>
</head>
<body>
<div class="wrap">
  <h1>LineagePulse</h1>
  <div class="accent"></div>
  <p class="sub">The first responder your data graph actually wakes up to.</p>

  <p>
    <span class="badge good">Live</span>
    <span class="badge">Apache 2.0</span>
    <span class="badge">18/18 tests</span>
    <span class="badge">3 sub-agents</span>
  </p>

  <div class="grid">
    <div class="card">
      <h3>Run the demo incident</h3>
      <p>A freshness violation on <code>taxi_trips</code> cascades into a downstream ML model. Watch the full pipeline execute.</p>
      <a class="btn" href="/demo">▶ Run demo</a>
    </div>
    <div class="card">
      <h3>PII compliance gap</h3>
      <p>A second scenario: a missing PII tag on a healthcare column. Proves the agent generalizes.</p>
      <a class="btn outline" href="/demo/pii">Run PII demo →</a>
    </div>
    <div class="card">
      <h3>Slack notification</h3>
      <p>The exact Block Kit payload the agent would post to a Slack channel.</p>
      <a class="btn outline" href="/slack">View Slack →</a>
    </div>
    <div class="card">
      <h3>DataHub Document</h3>
      <p>The structured incident record written back to the DataHub graph.</p>
      <a class="btn outline" href="/document">View Document →</a>
    </div>
    <div class="card">
      <h3>Full JSON report</h3>
      <p>Raw incident, blast radius, and LLM-authored root-cause report as JSON.</p>
      <a class="btn outline" href="/report">View JSON →</a>
    </div>
    <div class="card">
      <h3>GitHub repo</h3>
      <p>Read the source, run the test suite, and deploy your own.</p>
      <a class="btn outline" href="https://github.com/Donyemiight/lineagepulse">View repo →</a>
    </div>
  </div>

  <h2 style="margin-top: 48px;">What LineagePulse does</h2>
  <ul class="checks">
    <li>Reads the DataHub context graph (lineage, ownership, quality, ML metadata)</li>
    <li>Detects failing quality assertions, freshness violations, schema changes</li>
    <li>Walks the upstream + downstream blast radius automatically</li>
    <li>Bumps severity to CRITICAL if an ML model is in the downstream graph</li>
    <li>Writes a structured incident Document back to DataHub so the next agent inherits it</li>
    <li>Posts a per-owner Slack message with severity, blast radius, root cause, and fix</li>
  </ul>

  <footer>
    Built for the
    <a href="https://datahub.devpost.com">DataHub Agent Hackathon</a>
    · Source on
    <a href="https://github.com/Donyemiight/lineagepulse">GitHub</a>
    · Apache 2.0
  </footer>
</div>
</body>
</html>
"""


def _build_scenario(pii: bool = False) -> Incident:
    if pii:
        from lineagepulse.models import AssetRef, IncidentKind

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
                "The `email` column on `patients` does not have the `PII` glossary "
                "term applied. This is a compliance gap — three downstream reports "
                "inherit the column without masking."
            ),
            asset=asset,
            raw_signal={
                "missing_tag": "PII",
                "column": "email",
                "expected_owners": ["compliance@acme.io"],
            },
        )
        from lineagepulse.models import BlastRadius

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
        return incident
    incident = _synthesize_demo_incident()
    incident.blast_radius = _synthesize_blast_radius(incident.asset.urn)
    if incident.blast_radius.affected_ml_models:
        incident.severity = IncidentSeverity.CRITICAL
    return incident


# ----------------------------------------------------------------- routes
@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "lineagepulse", "dry_run": get_settings().dry_run}


@app.get("/demo", response_class=HTMLResponse)
def demo() -> str:
    return _render_scenario_html(_build_scenario(pii=False))


@app.get("/demo/pii", response_class=HTMLResponse)
def demo_pii() -> str:
    return _render_scenario_html(_build_scenario(pii=True))


@app.get("/slack")
def slack() -> JSONResponse:
    incident = _build_scenario(pii=False)
    settings = get_settings()
    report = investigate(incident, settings)
    incident._report = report  # type: ignore[attr-defined]
    blocks = render_blocks(incident, report, settings)
    return JSONResponse(content=blocks)


@app.get("/document", response_class=HTMLResponse)
def document() -> str:
    incident = _build_scenario(pii=False)
    settings = get_settings()
    report = investigate(incident, settings)
    incident._report = report  # type: ignore[attr-defined]
    body = _incident_to_document_body(incident)
    return _render_document_html(incident, body)


@app.get("/report")
def report() -> JSONResponse:
    incident = _build_scenario(pii=False)
    settings = get_settings()
    report = investigate(incident, settings)
    incident._report = report  # type: ignore[attr-defined]
    return JSONResponse(content={
        "incident": incident.model_dump(mode="json"),
        "report": report.model_dump(mode="json"),
    })


@app.get("/inspect/{urn:path}")
def inspect(urn: str) -> JSONResponse:
    settings = get_settings()
    client = DataHubClient(settings)
    asset = client.get_asset(urn)
    blast = client.get_lineage(urn, max_depth=settings.lineage_depth)
    return JSONResponse(content={
        "asset": asset.model_dump() if asset else None,
        "blast_radius": blast.model_dump(),
    })


# ----------------------------------------------------------------- renderers
def _render_scenario_html(incident: Incident) -> str:
    settings = get_settings()
    report = investigate(incident, settings)
    incident._report = report  # type: ignore[attr-defined]

    sev_color = {
        "low": "var(--good)",
        "medium": "var(--warn)",
        "high": "var(--danger)",
        "critical": "var(--danger)",
    }.get(incident.severity.value, "var(--fg)")

    blast = incident.blast_radius
    blast_html = ""
    if blast:
        def render_refs(refs, kind):
            if not refs:
                return ""
            items = "".join(
                f'<li><code>{r.name or r.urn.split(":")[-1]}</code> '
                f'<span style="color:var(--muted)">({r.type})</span></li>'
                for r in refs
            )
            return f'<h4>{kind} ({len(refs)})</h4><ul style="margin: 8px 0 16px;">{items}</ul>'

        blast_html = render_refs(blast.upstream, "Upstream")
        blast_html += render_refs(blast.downstream, "Downstream")
        if blast.affected_ml_models:
            blast_html += render_refs(blast.affected_ml_models, "🤖 ML models")
        if blast.affected_dashboards:
            blast_html += render_refs(blast.affected_dashboards, "Dashboards")
        if blast.affected_pipelines:
            blast_html += render_refs(blast.affected_pipelines, "Pipelines")

    actions_html = "".join(f"<li>{a}</li>" for a in report.recommended_actions)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{incident.title} · LineagePulse</title>
<style>
  body {{ margin: 0; background: var(--bg); color: var(--fg); font-family: -apple-system, "SF Pro Display", "Inter", sans-serif; line-height: 1.55; }}
  :root {{ --bg: #0f172a; --fg: #f8fafc; --muted: #64748b; --accent: #38bdf8; --danger: #ef4444; --warn: #fbbf24; --good: #22c55e; --card: #1e293b; --line: #334155; }}
  .wrap {{ max-width: 920px; margin: 0 auto; padding: 48px 32px; }}
  h1 {{ font-size: 36px; color: {sev_color}; margin: 0; }}
  h2 {{ font-size: 18px; color: var(--accent); margin: 32px 0 8px; text-transform: uppercase; letter-spacing: 0.05em; }}
  h4 {{ margin: 8px 0 4px; color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .meta {{ color: var(--muted); font-size: 14px; margin-top: 8px; }}
  .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; background: {sev_color}; color: #fff; margin-right: 8px; }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 24px; margin: 16px 0; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 4px 0; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a.btn {{ display: inline-block; padding: 8px 16px; background: var(--accent); color: var(--bg); border-radius: 8px; font-weight: 600; font-size: 13px; }}
  pre {{ background: #020617; border: 1px solid var(--line); border-radius: 8px; padding: 16px; overflow-x: auto; font-size: 13px; }}
  code {{ font-family: "SF Mono", "JetBrains Mono", Menlo, monospace; }}
  .toolbar {{ margin-bottom: 24px; }}
  .toolbar a {{ margin-right: 12px; font-size: 13px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="toolbar">
    <a href="/">← Home</a>
    <a href="/slack">Slack</a>
    <a href="/document">Document</a>
    <a href="/report">JSON</a>
  </div>

  <span class="badge">{incident.severity.value.upper()}</span>
  <span style="color:var(--muted); font-size:13px;">{incident.kind.value}</span>
  <h1>{incident.title}</h1>
  <p class="meta">
    Asset: <code>{incident.asset.urn}</code> · Detected: {incident.detected_at.strftime("%Y-%m-%d %H:%M UTC")}
  </p>

  <div class="card">
    <h2>Summary</h2>
    <p>{report.executive_summary}</p>
  </div>

  <div class="card">
    <h2>Root cause hypothesis</h2>
    <p>{report.root_cause_hypothesis}</p>
  </div>

  <div class="card">
    <h2>Suggested fix</h2>
    <p>{report.suggested_fix}</p>
  </div>

  <div class="card">
    <h2>Recommended actions</h2>
    <ul>{actions_html}</ul>
  </div>

  <div class="card">
    <h2>Blast radius</h2>
    {blast_html}
  </div>

  <div class="card">
    <h2>Owners</h2>
    <p>{", ".join(incident.asset.owners) if incident.asset.owners else "_(none on file)_"}</p>
  </div>

  <p style="color:var(--muted); font-size:13px; margin-top:32px;">
    Generated by LineagePulse · DataHub Agent Hackathon submission
  </p>
</div>
</body>
</html>
"""


def _render_document_html(incident: Incident, body: str) -> str:
    # Render the Markdown body as HTML for display
    import re

    html = body
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    # Wrap consecutive <li> in <ul>
    html = re.sub(r"((?:<li>.*?</li>\n?)+)", r"<ul>\1</ul>", html, flags=re.DOTALL)
    # Paragraphs
    html = re.sub(r"\n\n", r"</p><p>", html)
    html = "<p>" + html + "</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>DataHub Document · LineagePulse</title>
<style>
  :root {{ --bg: #f8fafc; --fg: #0f172a; --muted: #64748b; --accent: #38bdf8; --line: #e2e8f0; }}
  body {{ margin: 0; background: var(--bg); color: var(--fg); font-family: -apple-system, "SF Pro Display", "Inter", sans-serif; line-height: 1.6; }}
  .wrap {{ max-width: 760px; margin: 0 auto; padding: 48px 32px; }}
  .toolbar {{ margin-bottom: 24px; }}
  .toolbar a {{ color: var(--muted); margin-right: 12px; font-size: 13px; text-decoration: none; }}
  .doc {{ background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 32px 40px; }}
  h1 {{ font-size: 32px; margin: 0 0 24px; }}
  h2 {{ color: var(--accent); font-size: 20px; margin: 32px 0 8px; }}
  code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 13px; font-family: "SF Mono", monospace; }}
  ul {{ padding-left: 20px; }}
  hr {{ border: none; border-top: 1px solid var(--line); margin: 32px 0; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="toolbar">
    <a href="/">← Home</a>
    <a href="/demo">Demo</a>
    <a href="/slack">Slack</a>
  </div>
  <div class="doc">
    {html}
  </div>
</div>
</body>
</html>
"""


# ----------------------------------------------------------------- settings
def get_settings() -> Settings:
    return Settings(
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
        datahub_gms_url=os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"),
        datahub_token=os.getenv("DATAHUB_TOKEN"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
    )
