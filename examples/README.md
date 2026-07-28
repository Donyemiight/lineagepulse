# LineagePulse — Examples

This directory contains deterministic example outputs from the LineagePulse agent.
Every JSON and Markdown file here is the exact payload a judge would see if they
ran `scripts/demo_runbook.py` themselves.

The goal is that the submission stands on its own: a judge can read these files
end-to-end without running any code, without a DataHub instance, and without an
LLM key.

## Files

| File | What it shows |
|---|---|
| `demo_output/incident.json` | The `Incident` object the Detector hands the Investigator. |
| `demo_output/report.json` | The LLM-authored root-cause + fix plan (IncidentReport). |
| `demo_output/slack_blocks.json` | The exact Slack Block Kit payload that would be posted. |
| `demo_output/slack_blocks.md` | Human-readable rendering of the Slack message. |
| `demo_output/datahub_document.md` | The exact DataHub Document that gets written back to the graph. |
| `smoke_test_output.json` | Output of `scripts/smoke_test.py` — the end-to-end CI artifact. |

## Scenarios

The demo runbook uses the `nyc-taxi` sample dataset scenario from the
DataHub hackathon resources:

> A freshness violation on `taxi_trips` has gone unnoticed for 3h 12m.
> The downstream aggregate `daily_revenue` is now stale. The ML model
> `demand_forecaster` is training on stale features. The `Daily Ops`
> Looker dashboard is also affected.

This is the *exact* scenario the DataHub team planted in the
`nyc-taxi` sample dataset — when you point the agent at a real
DataHub instance with that datapack loaded, the Detector picks up
the real failing assertion.

To run it against a real DataHub:

```bash
datahub docker quickstart
datahub datapack load nyc-taxi
export DATAHUB_GMS_URL=http://localhost:8080
export DATAHUB_TOKEN=<your token from Settings → Access Tokens>
export ANTHROPIC_API_KEY=<your key>
unset DRY_RUN
python -m lineagepulse run --once
```

## Regenerate

```bash
python scripts/demo_runbook.py    # writes to examples/demo_output/
python scripts/smoke_test.py      # writes to examples/smoke_test_output.json
```
