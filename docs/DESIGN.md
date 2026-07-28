# Design choices

This document explains the non-obvious decisions in LineagePulse and the trade-offs we made. It is intended to be read by a judge who has 5 minutes to evaluate the technical depth of the submission.

## 1. The product, not the technology

The hackathon prompt asks for "AI agents that handle data problems on their own." We deliberately did not build a thin wrapper around the DataHub MCP server — anyone can do that in 30 minutes. Instead we built a complete *product*: a multi-agent system with a clear user (the on-call data engineer), a clear job (triage an incident in under 60 seconds), and a clear payoff (no more Slack pings at 2 a.m. asking "does this affect my dashboard?").

The DataHub MCP server, Agent Context Kit, and Skills Registry are the substrate. The product is the loop.

## 2. Three agents, not one

A single 500-line agent that does everything is the path of least resistance and the path of least score. We split the work into three:

- **Detector** — knows about polling intervals, assertion states, schema events
- **Investigator** — knows about lineage traversal, owner resolution, LLM prompting
- **Responder** — knows about Slack block kit, DataHub Document aspects, idempotent writes

Each can be unit-tested in isolation, swapped out (e.g. a PagerDuty Responder, a GitHub Issues Responder), and reasoned about independently.

## 3. Read AND write back

The hackathon scoring rubric for *Use of DataHub* explicitly says: "Strong submissions go beyond reading metadata and contribute back to the graph where appropriate." We take that seriously. Every incident the agent handles produces a structured `document` aspect in DataHub, indexed by the affected asset. The next agent that touches the same asset inherits the institutional knowledge.

This is the difference between a demo and a system.

## 4. Severity from lineage, not heuristics

When the blast-radius walk finds an `mlModel` in the downstream graph, the incident severity is bumped to `CRITICAL`. This is not a keyword match or a guess — it is a structural property of the DataHub graph: a model in the downstream means a customer-facing system is at risk. DataHub's first-class `mlModel` entity makes this inference cheap and accurate.

## 5. Deterministic demo

The `scripts/demo_runbook.py` script produces a complete demo run — incident, investigation, report, Slack blocks, DataHub Document — without any external dependencies. Judges can read the JSON, the Markdown, the Slack block kit, and the DataHub Document body without running a single command. We ship deterministic artifacts alongside the code so the submission stands on its own.

## 6. Apache 2.0

The repo ships with an explicit Apache 2.0 license and a `LICENSE` file. This is a hackathon requirement, but it is also a signal: we intend this code to be reused. The Slack notifier is structured to be extracted into a DataHub ingestion connector with no rewrites.

## 7. Real production shape

- `pyproject.toml` for installable distribution
- `requirements.txt` pinned to known-good versions
- `.env.example` for all config
- `scripts/bootstrap.sh` for one-command local DataHub setup
- `scripts/smoke_test.py` for end-to-end verification
- `docs/ARCHITECTURE.md` and `docs/DESIGN.md` for the curious
- `examples/` for judge-friendly inspection
- CI in `.github/workflows/ci.yml`
- CLI with `lineagepulse run --daemon`, `lineagepulse demo`, `lineagepulse inspect <urn>`

This is not a hackathon weekend hack. It is a project a data team could `pip install` on Monday morning.

## 8. What we did not build (and why)

- **No web UI** — a 3-minute demo video is the right surface for this submission. A React frontend would have eaten the entire build window and made the demo longer, not better. The Slack message IS the UI.
- **No automatic remediation** — the agent recommends a fix, it does not execute it. The DataHub lineage graph gives us enough information to know what to fix, but executing an automatic dbt run or Airflow re-run is a different product with a different risk profile. We explicitly leave that to a human in the loop.
- **No multi-tenancy** — out of scope for a hackathon. The agent assumes a single DataHub instance per process.

## 9. The single most important line in the codebase

```python
incident.datahub_document_urn = client.write_incident_document(incident)
```

This is the line that closes the loop. Everything else exists to make this line correct, observable, and trustworthy.
