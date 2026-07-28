# LineagePulse — DataHub Agent Hackathon submission

**Sub-challenge:** Agents That Do Real Work *(also touches Production ML Agents)*

**Repository:** https://github.com/Donyemiight/lineagepulse
**Live demo URL:** https://lineagepulse.onrender.com *(judges can click this — no install needed)*
**Demo video:** https://github.com/Donyemiight/lineagepulse/blob/main/docs/lineagepulse-demo.mp4 *(to be uploaded to YouTube by the maintainer)*
**Local test entry point:** `python -m lineagepulse demo`

---

## What it does (Devpost "Built with" field)

Built on top of the **DataHub Agent Context Kit** (`datahub-agent-context`),
**MCP Server** tool surface, and **Skills Registry**, LineagePulse is a
three-agent system that closes the **DataHub → Slack → DataHub** incident
response loop.

When a data quality assertion fails or a schema changes on a critical
asset, the agent:

1. **Detector** polls DataHub via the `get_dataset_assertions` and
   `search` tools and pulls the failing signal.
2. **Investigator** walks upstream + downstream lineage with
   `get_lineage`, attaches owner / domain / description / quality data
   via `get_entities`, and asks an LLM to author a structured
   root-cause + fix report.
3. **Responder** writes a structured incident **Document** back to
   DataHub using `save_document`, then posts a per-owner Slack message
   with severity, blast radius, root-cause, and the suggested fix.

When the blast-radius walk finds an `mlModel` downstream, the incident
is automatically bumped to **CRITICAL** — because a broken dataset that
feeds a production model is a different class of problem than a broken
dashboard. DataHub's first-class ML lineage entity makes this inference
cheap and accurate.

## What's novel

- **Multi-agent architecture** — three cooperating sub-agents
  (Detector, Investigator, Responder) with separate tool surfaces,
  following the same LangGraph pattern DataHub's own Analytics Agent
  uses. Each is independently testable.
- **Closes the loop** — the incident Document is persisted back to
  DataHub so the next agent that touches the same asset inherits the
  knowledge. The hackathon's "Use of DataHub" criterion explicitly
  rewards this property.
- **ML-aware severity** — automatic CRITICAL bump when an ML model is
  in the downstream blast radius, derived from DataHub's `mlModel`
  lineage entity, not from heuristics.
- **Production-shaped** — Apache 2.0, pip-installable, 18 unit tests,
  a deterministic demo runbook that runs with zero external
  credentials, and a CI workflow definition.

## What we used from the DataHub stack

| Surface | Tool / API |
|---|---|
| Agent Context Kit (LangChain tools) | `search`, `get_entities`, `get_lineage`, `list_schema_fields`, `get_dataset_queries`, `get_dataset_assertions`, `search_documents`, `save_document` |
| SDK | `datahub.sdk.main_client.DataHubClient` |
| Context graph | lineage, ownership, domains, quality signals, ML metadata |
| Skills Registry | (project structure follows the same pattern) |

## How to test it (judges, ~3 minutes)

```bash
# Option 1 — zero credentials, deterministic demo
git clone https://github.com/Donyemiight/lineagepulse.git
cd lineagepulse
pip install -e .
python scripts/smoke_test.py
python scripts/demo_runbook.py
# Open examples/demo_output/ — Slack JSON, DataHub document MD, incident JSON

# Option 2 — full live demo
datahub docker quickstart
datahub datapack load nyc-taxi
export DATAHUB_GMS_URL=http://localhost:8080
export DATAHUB_TOKEN=<from Settings → Access Tokens>
export ANTHROPIC_API_KEY=<your key>
export SLACK_WEBHOOK_URL=<optional>
python -m lineagepulse run --once
```

The second demo (`scripts/demo_runbook_pii.py`) covers a PII-tag
compliance gap on the `healthcare` dataset, proving the agent
generalizes beyond freshness assertions.

## Tech

- **Language:** Python 3.10+
- **Stack:** `datahub-agent-context`, `acryl-datahub`, LangGraph, LangChain, Anthropic Claude (or OpenAI), Slack incoming webhooks
- **License:** Apache 2.0
- **Tests:** 18 unit tests covering the DataHub client, the agent orchestrator, and the Slack notifier

## Why I built this

I'm a serial hackathon builder on data/AI infra. In every data team I've
seen, the worst on-call minutes are spent in DataHub itself — clicking
through lineage, copying owner emails into Slack, trying to remember if
the failing dashboard is the same one Finance uses. LineagePulse turns
that 90-minute investigation into a 90-second Slack thread, and writes
the result back so no one has to do it again.

---

## Built for the DataHub Agent Hackathon · 2026
