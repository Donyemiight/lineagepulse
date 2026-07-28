"""LLM client abstraction.

We keep the LLM behind a small interface so we can run end-to-end
smoke tests in ``DRY_RUN`` mode without burning tokens, and so we can
swap Anthropic ↔ OpenAI by changing one env var.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from lineagepulse.config import Settings
from lineagepulse.models import Incident, IncidentReport

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are LineagePulse, an expert data platform incident responder.

You receive a structured incident with: failing asset, lineage blast radius,
owner list, and the raw failure signal. Your job is to produce a clear,
actionable incident report a human on-call engineer can act on in 60 seconds.

Rules:
- Be specific. Name the asset, the failure, the downstream consumers.
- Recommend the smallest viable fix, then the larger one.
- If the blast radius includes an ML model in production, treat that as
  CRITICAL severity and flag it explicitly.
- Do not invent URNs or owners — only use what is provided.
- Output strict JSON matching the schema in the prompt.
"""


def build_llm(settings: Settings) -> BaseChatModel | None:
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return ChatAnthropic(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.anthropic_api_key,
        )
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )
    return None


def investigate(incident: Incident, settings: Settings) -> IncidentReport:
    """Use the LLM to author a root-cause narrative + suggested fix."""
    fallback = _fallback_report(incident)
    llm = build_llm(settings)
    if llm is None:
        logger.info("LLM not configured — using heuristic report")
        return fallback

    user_prompt = _build_investigation_prompt(incident)

    try:
        response = llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
        )
        text = response.content if isinstance(response.content, str) else str(response.content)
        return _parse_report(text) or fallback
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM investigation failed: %s", exc)
        return fallback


# ------------------------------------------------------------------ helpers
def _build_investigation_prompt(incident: Incident) -> str:
    import json

    payload = {
        "incident": {
            "id": incident.id,
            "kind": incident.kind.value,
            "title": incident.title,
            "summary": incident.summary,
            "severity": incident.severity.value,
            "asset": {
                "urn": incident.asset.urn,
                "name": incident.asset.name,
                "platform": incident.asset.platform,
                "owners": incident.asset.owners,
                "domain": incident.asset.domain,
            },
            "raw_signal": incident.raw_signal,
        },
        "blast_radius": _blast_radius_to_dict(incident.blast_radius) if incident.blast_radius else None,
        "schema_hints": "Look for: target leakage, schema drift, freshness violations, "
                        "missing descriptions, broken lineage edges, PII exposure, "
                        "ML training-serving skew.",
        "response_schema": {
            "title": "string — concise incident title",
            "executive_summary": "string — 2-3 sentences, what a VP needs to know",
            "root_cause_hypothesis": "string — best technical guess with evidence",
            "suggested_fix": "string — concrete next action(s)",
            "blast_radius_summary": "string — who/what is affected in human terms",
            "severity_rationale": "string — why this severity, what would change it",
            "recommended_actions": ["list of short, ordered action strings"],
        },
    }
    return (
        "Investigate the following incident and return JSON matching the schema.\n\n"
        f"```json\n{json.dumps(payload, indent=2, default=str)}\n```"
    )


def _blast_radius_to_dict(br) -> dict[str, Any]:
    return {
        "root_urn": br.root.urn,
        "upstream_count": len(br.upstream),
        "downstream_count": len(br.downstream),
        "ml_models": [m.urn for m in br.affected_ml_models],
        "dashboards": [d.urn for d in br.affected_dashboards],
        "pipelines": [p.urn for p in br.affected_pipelines],
    }


def _parse_report(text: str) -> IncidentReport | None:
    import json
    import re

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return IncidentReport(**data)
    except Exception as exc:  # noqa: BLE001
        logger.debug("parse_report failed: %s", exc)
        return None


def _fallback_report(incident: Incident) -> IncidentReport:
    """No-LLM report. Heuristic, still useful for tests."""
    br = incident.blast_radius
    blast_summary = "no lineage available"
    if br is not None:
        parts = []
        if br.downstream:
            parts.append(f"{len(br.downstream)} downstream consumer(s)")
        if br.affected_ml_models:
            parts.append(f"{len(br.affected_ml_models)} ML model(s)")
        if br.affected_dashboards:
            parts.append(f"{len(br.affected_dashboards)} dashboard(s)")
        if parts:
            blast_summary = ", ".join(parts)
    return IncidentReport(
        title=incident.title,
        executive_summary=incident.summary,
        root_cause_hypothesis=(
            "The configured LLM is not available, so a heuristic root cause is reported. "
            f"Inspect the raw signal: {incident.raw_signal}"
        ),
        suggested_fix=(
            "Re-run the upstream pipeline, then re-validate the assertion. "
            "If it persists, check the most recent schema change on the upstream dataset."
        ),
        blast_radius_summary=blast_summary,
        severity_rationale=f"Severity is set to {incident.severity.value} based on the signal type.",
        recommended_actions=[
            "Re-run the upstream pipeline producing this asset.",
            "Verify the assertion definition still matches the current schema.",
            "Notify the listed owners if the issue persists after re-run.",
        ],
    )
