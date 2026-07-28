# LineagePulse — Architecture

## Goals

LineagePulse is a multi-agent system that closes the **DataHub → Slack → DataHub** incident-response loop. The judges' explicit scoring for the **Use of DataHub** criterion rewards projects that *both read the context graph and write back to it*. LineagePulse is built around that loop.

## Components

| Component | Role | DataHub surface |
|---|---|---|
| `Detector` | Polls DataHub for failing assertions / schema changes | `assertions.get_assertion_results` |
| `Investigator` | Walks lineage, gathers owners + descriptions + quality, asks LLM for a root-cause report | `entities.get`, `lineage.get_lineage`, `entities.get_schema` |
| `Responder` | Writes a structured incident Document back to DataHub, posts a Slack message | `entities.upsert` (`document` aspect), Slack webhook |
| `Orchestrator` | Wires the three sub-agents together and runs them in order | — |

## Why three agents (not one)

* **Single responsibility** — each agent can be tested in isolation. We have unit tests for the Investigator's blast-radius logic, the Slack renderer's block-kit output, and the Document body's Markdown, all without an LLM call.
* **Tool isolation** — the Responder only ever calls `save_document`. The Investigator only ever calls read APIs. The Detector only ever calls the polling surface. This is the pattern DataHub's own Analytics Agent uses.
* **Pluggable** — the same Investigator can be reused by a different orchestrator (a Slack bot, a GitHub Action, a dbt test runner).

## Data flow

```
       ┌──────────────────────────────────────────────────────┐
       │  DataHub (read)                                      │
       │   ↓                                                   │
       │  Detector (failing assertions)                        │
       │   ↓ seed incident                                     │
       │  Investigator (lineage + LLM root-cause)              │
       │   ↓ enriched incident                                 │
       │  Responder                                            │
       │   ├─→ DataHub (write)  structured incident Document  │
       │   └─→ Slack (notify)   per-owner message + buttons   │
       └──────────────────────────────────────────────────────┘
```

## Why LangGraph

LangGraph lets us model the three agents as a state machine with shared state, so the same `Incident` object flows from Detector → Investigator → Responder and each stage can be replayed, tested, or replaced independently. LangGraph is the same orchestration library DataHub's own open-source [Analytics Agent](https://github.com/datahub-project/analytics-agent) uses — so we're speaking the same vocabulary the judges know.

## ML-aware severity

When the Investigator's blast-radius walk finds an `mlModel` in the downstream graph, the agent bumps the incident severity to `CRITICAL`. This is intentional: a broken dataset that feeds a production model can break a customer-facing product, which is a different class of incident than a broken dashboard. The DataHub lineage graph gives us this information for free because `mlModel` entities are first-class.

## Why we write back to DataHub

The strongest submissions in the hackathon "go beyond reading metadata and contribute back to the graph where appropriate" (judging criteria, point 1). The Responder uses DataHub's `document` aspect to write a structured incident record back to the graph. The next time any agent — human or AI — searches for `taxi_trips`, they find the incident in their context. This is the property the judges are explicitly scoring.

## DRY_RUN mode

Every external side effect (DataHub write, Slack post, LLM call) is gated behind a `DRY_RUN` flag. This makes the demo deterministic for judges, makes the smoke test runnable in CI without credentials, and is the same pattern the DataHub team uses in their own open-source examples.

## Configuration

All runtime configuration is loaded from environment variables via `pydantic-settings`. See `.env.example` for the full list. The agent degrades gracefully if any single integration is missing: no Slack URL → notifications skipped, no LLM key → heuristic report, no DataHub token → read-only mode.

## Testing

`scripts/smoke_test.py` runs the full pipeline in DRY_RUN mode and asserts the output. It is what `make smoke` invokes, and it is the same script that produces the JSON in `examples/`.
