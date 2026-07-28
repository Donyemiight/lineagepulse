"""Thin, dependency-injectable wrapper around the DataHub SDK.

This is the single integration point with DataHub. It uses the
**official DataHub Agent Context Kit** (``datahub-agent-context``) and
its LangChain tool bindings as the primary surface — the same SDK
DataHub ships for building AI agents.

We isolate the DataHub API behind this class so the rest of the agent
is testable without a live DataHub instance, and so we can swap the
underlying SDK (agent-context-kit, raw GraphQL, or the MCP server)
without touching the agent logic.

Two surfaces are used:

* **Read** — ``search``, ``get_entities``, ``get_lineage``,
  ``list_schema_fields``, ``get_dataset_queries``,
  ``get_dataset_assertions``, ``search_documents``.
* **Write** — ``save_document``. Opt-in via
  ``DATAHUB_MUTATIONS_ENABLED``. The agent only writes a structured
  incident document back to the graph.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from lineagepulse.config import Settings
from lineagepulse.models import (
    AssetRef,
    BlastRadius,
    Incident,
    IncidentKind,
    IncidentSeverity,
    IncidentStatus,
)

logger = logging.getLogger(__name__)


class DataHubClient:
    """Reads the context graph and writes incident documents back."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Any = None
        self._read_tools: dict[str, Any] = {}
        self._write_tools: dict[str, Any] = {}
        self._init_error: str | None = None

    # ------------------------------------------------------------------ init
    def _ensure_client(self) -> None:
        if self._client is not None or self._init_error is not None:
            return
        try:
            from datahub.sdk.main_client import DataHubClient as _Native
            from datahub_agent_context.langchain_tools import build_langchain_tools

            kwargs: dict[str, Any] = {"server": self.settings.datahub_gms_url}
            if self.settings.datahub_token:
                kwargs["token"] = self.settings.datahub_token
            self._client = _Native(**kwargs)

            for tool in build_langchain_tools(self._client, include_mutations=False):
                self._read_tools[tool.name] = tool
            for tool in build_langchain_tools(
                self._client,
                include_mutations=self.settings.datahub_mutations_enabled,
            ):
                self._write_tools[tool.name] = tool
            logger.info(
                "DataHub connected: %s (read=%d write=%d tools)",
                self.settings.datahub_gms_url,
                len(self._read_tools),
                len(self._write_tools),
            )
        except Exception as exc:  # noqa: BLE001
            self._init_error = str(exc)
            logger.warning("DataHub client unavailable: %s", exc)

    @property
    def available(self) -> bool:
        self._ensure_client()
        return self._client is not None

    @property
    def tools_summary(self) -> dict[str, list[str]]:
        return {
            "read": sorted(self._read_tools.keys()),
            "write": sorted(self._write_tools.keys()),
        }

    # ------------------------------------------------------------- read API
    def search(
        self,
        query: str,
        *,
        entity_types: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        self._ensure_client()
        tool = self._read_tools.get("search")
        if not tool:
            return []
        try:
            res = tool.invoke({"query": query, "limit": limit})
            return _coerce_to_list_of_dicts(res)
        except Exception as exc:  # noqa: BLE001
            logger.warning("search failed: %s", exc)
            return []

    def get_asset(self, urn: str) -> AssetRef | None:
        self._ensure_client()
        tool = self._read_tools.get("get_entities")
        if not tool:
            return None
        try:
            res = tool.invoke({"urns": [urn]})
            data = _first_dict(res)
            if not data:
                return None
            return _dict_to_asset_ref(data, urn)
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_asset(%s) failed: %s", urn, exc)
            return None

    def get_lineage(
        self,
        urn: str,
        *,
        direction: str = "both",
        max_depth: int = 3,
    ) -> BlastRadius:
        root = self.get_asset(urn) or AssetRef(urn=urn)
        blast = BlastRadius(root=root)
        self._ensure_client()
        tool = self._read_tools.get("get_lineage")
        if not tool:
            return blast

        for direction_ in (
            ["upstream"] if direction in ("upstream", "both") else []
        ) + (["downstream"] if direction in ("downstream", "both") else []):
            try:
                res = tool.invoke({"urn": urn, "direction": direction_, "max_hops": max_depth})
                refs = _lineage_response_to_refs(res, direction_)
                if direction_ == "upstream":
                    blast.upstream = refs
                else:
                    blast.downstream = refs
                    for r in refs:
                        if r.type == "mlModel":
                            blast.affected_ml_models.append(r)
                        elif r.type == "dashboard":
                            blast.affected_dashboards.append(r)
                        elif r.type == "dataJob":
                            blast.affected_pipelines.append(r)
            except Exception as exc:  # noqa: BLE001
                logger.debug("lineage %s for %s failed: %s", direction_, urn, exc)
        return blast

    def list_schema_fields(self, urn: str) -> list[dict[str, Any]]:
        self._ensure_client()
        tool = self._read_tools.get("list_schema_fields")
        if not tool:
            return []
        try:
            res = tool.invoke({"urn": urn})
            return _coerce_to_list_of_dicts(res)
        except Exception as exc:  # noqa: BLE001
            logger.debug("schema fetch failed: %s", exc)
            return []

    def get_dataset_assertions(self, urn: str) -> list[dict[str, Any]]:
        """Pull data quality assertions for a dataset."""
        self._ensure_client()
        tool = self._read_tools.get("get_dataset_assertions")
        if not tool:
            return []
        try:
            res = tool.invoke({"urn": urn})
            return _coerce_to_list_of_dicts(res)
        except Exception as exc:  # noqa: BLE001
            logger.debug("assertion fetch failed: %s", exc)
            return []

    def search_documents(self, query: str) -> list[dict[str, Any]]:
        """Find prior incident documents for an asset."""
        self._ensure_client()
        tool = self._read_tools.get("search_documents")
        if not tool:
            return []
        try:
            res = tool.invoke({"query": query})
            return _coerce_to_list_of_dicts(res)
        except Exception as exc:  # noqa: BLE001
            logger.debug("document search failed: %s", exc)
            return []

    # ---------------------------------------------------------- polling API
    def fetch_failing_assertions(self, lookback_hours: int = 24) -> list[Incident]:
        """Poll for currently-failing assertions across the catalog."""
        self._ensure_client()
        if not self._read_tools:
            return []
        incidents: list[Incident] = []

        # 1. Find candidate datasets via search
        candidates: list[str] = []
        try:
            for hit in self.search("freshness", limit=50):
                urn = hit.get("urn") or hit.get("entity_urn")
                if urn:
                    candidates.append(urn)
            for hit in self.search("quality", limit=50):
                urn = hit.get("urn") or hit.get("entity_urn")
                if urn:
                    candidates.append(urn)
        except Exception as exc:  # noqa: BLE001
            logger.debug("candidate scan failed: %s", exc)

        seen: set[str] = set()
        for dataset_urn in candidates:
            if dataset_urn in seen:
                continue
            seen.add(dataset_urn)
            assertions = self.get_dataset_assertions(dataset_urn)
            for a in assertions:
                state = (a.get("state") or a.get("result_state") or "").upper()
                if state not in ("FAILURE", "ERROR", "WARNING"):
                    continue
                asset = self.get_asset(dataset_urn) or AssetRef(urn=dataset_urn)
                kind = (
                    IncidentKind.FRESHNESS_VIOLATION
                    if "freshness" in (a.get("type") or a.get("assertion_type") or "").lower()
                    else IncidentKind.ASSERTION_FAILURE
                )
                incidents.append(
                    Incident(
                        kind=kind,
                        severity=_severity_from_state(state),
                        title=f"Assertion failure on {asset.name or asset.urn}",
                        summary=a.get("message") or a.get("description") or "Assertion failed without a message.",
                        asset=asset,
                        source="datahub:assertions",
                        source_id=a.get("urn") or a.get("assertion_urn"),
                        raw_signal=a,
                    )
                )
        return incidents

    # ------------------------------------------------------------- write API
    def write_incident_document(self, incident: Incident) -> str | None:
        """Persist a structured incident document back to DataHub.

        Uses the ``save_document`` tool from the DataHub Agent Context
        Kit. Returns the document URN on success.
        """
        if not self.settings.datahub_mutations_enabled:
            logger.info("mutations disabled — skipping writeback")
            return None
        if self.settings.dry_run:
            logger.info("DRY_RUN — would write document for %s", incident.id)
            return None
        self._ensure_client()
        tool = self._write_tools.get("save_document")
        if not tool:
            logger.warning("save_document tool unavailable — writeback skipped")
            return None
        try:
            body = _incident_to_document_body(incident)
            doc_urn = f"urn:li:document:incident-{incident.id}"
            res = tool.invoke(
                {
                    "urn": doc_urn,
                    "title": incident.title,
                    "contents": body,
                    "related_urns": [incident.asset.urn],
                }
            )
            incident.datahub_document_urn = doc_urn
            incident.status = IncidentStatus.DOCUMENTED
            logger.info("Wrote document %s (tool returned %s)", doc_urn, res)
            return doc_urn
        except Exception as exc:  # noqa: BLE001
            logger.warning("writeback failed: %s", exc)
            return None


# --------------------------------------------------------------------- helpers
def _coerce_to_list_of_dicts(obj: Any) -> list[dict[str, Any]]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return [d for d in (_to_dict(x) for x in obj) if d is not None]
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)
            if isinstance(parsed, list):
                return [d for d in (_to_dict(x) for x in parsed) if d is not None]
            d = _to_dict(parsed)
            return [d] if d is not None else []
        except json.JSONDecodeError:
            return []
    d = _to_dict(obj)
    return [d] if d is not None else []


def _first_dict(obj: Any) -> dict[str, Any] | None:
    items = _coerce_to_list_of_dicts(obj)
    return items[0] if items else None


def _to_dict(obj: Any) -> dict[str, Any] | None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:  # noqa: BLE001
            logger.debug("model_dump failed on %s", type(obj).__name__)
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:  # noqa: BLE001
            logger.debug("dict() failed on %s", type(obj).__name__)
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {"value": str(obj)}


def _dict_to_asset_ref(d: dict[str, Any], urn: str) -> AssetRef:
    platform = d.get("platform") or d.get("data_platform")
    if isinstance(platform, dict):
        platform = platform.get("name")
    return AssetRef(
        urn=urn,
        type=_platform_to_type(platform or d.get("entity_type") or d.get("type")),
        platform=str(platform) if platform else None,
        name=d.get("name") or d.get("display_name") or d.get("properties", {}).get("name"),
        owners=_extract_owners(d.get("ownership") or d.get("owners")),
        domain=_extract_domain(d.get("domain")),
    )


def _extract_owners(ownership: Any) -> list[str]:
    out: list[str] = []
    if isinstance(ownership, dict):
        owners = ownership.get("owners", [])
    elif isinstance(ownership, list):
        owners = ownership
    else:
        return []
    for o in owners:
        if isinstance(o, dict):
            v = o.get("owner") or o.get("urn") or o.get("username")
            if v:
                out.append(str(v).split(":")[-1] if ":" in str(v) else str(v))
    return out


def _extract_domain(domain: Any) -> str | None:
    if isinstance(domain, dict):
        return domain.get("name") or domain.get("domain")
    if isinstance(domain, str):
        return domain.split(":")[-1] if ":" in domain else domain
    return None


def _lineage_response_to_refs(res: Any, direction: str) -> list[AssetRef]:
    out: list[AssetRef] = []
    items = _coerce_to_list_of_dicts(res)
    for item in items:
        if not isinstance(item, dict):
            continue
        urn = (
            item.get("urn")
            or item.get("entity_urn")
            or item.get(f"{direction}_urn")
            or item.get("destinationUrn")
            or item.get("sourceUrn")
        )
        if not urn:
            continue
        platform = item.get("platform") or item.get("data_platform")
        if isinstance(platform, dict):
            platform = platform.get("name")
        out.append(
            AssetRef(
                urn=urn,
                type=_platform_to_type(platform or item.get("type")),
                platform=str(platform) if platform else None,
                name=item.get("name"),
            )
        )
    return out


def _platform_to_type(platform: Any) -> str:
    s = str(platform).lower() if platform else ""
    if any(p in s for p in ("snowflake", "bigquery", "redshift", "databricks", "postgres", "mysql", "s3", "kafka")):
        return "dataset"
    if any(p in s for p in ("mlflow", "sagemaker", "model", "vertex")):
        return "mlModel"
    if any(p in s for p in ("looker", "tableau", "powerbi", "superset", "metabase")):
        return "dashboard"
    if any(p in s for p in ("airflow", "spark", "dagster", "prefect", "dbt")):
        return "dataJob"
    if "model" in s:
        return "mlModel"
    if "dashboard" in s or "chart" in s:
        return "dashboard"
    return "dataset"


def _severity_from_state(state: str) -> IncidentSeverity:
    s = state.upper()
    if s in ("FAILURE", "ERROR"):
        return IncidentSeverity.HIGH
    if s == "WARNING":
        return IncidentSeverity.MEDIUM
    return IncidentSeverity.LOW


def _incident_to_document_body(incident: Incident) -> str:
    """Render an Incident as a Markdown body for a DataHub Document aspect."""
    lines: list[str] = []
    lines.append(f"# {incident.title}")
    lines.append("")
    lines.append(f"- **Incident ID**: `{incident.id}`")
    lines.append(f"- **Kind**: `{incident.kind.value}`")
    lines.append(f"- **Severity**: **{incident.severity.value.upper()}**")
    lines.append(f"- **Detected at**: {incident.detected_at.isoformat()}")
    lines.append(f"- **Asset**: `{incident.asset.urn}`")
    if incident.asset.owners:
        lines.append(f"- **Owners**: {', '.join(incident.asset.owners)}")
    if incident.asset.domain:
        lines.append(f"- **Domain**: {incident.asset.domain}")
    lines.append("")
    lines.append("## Summary")
    lines.append(incident.summary)
    if incident.root_cause:
        lines.append("")
        lines.append("## Root cause hypothesis")
        lines.append(incident.root_cause)
    if incident.suggested_fix:
        lines.append("")
        lines.append("## Suggested fix")
        lines.append(incident.suggested_fix)
    if incident.blast_radius:
        br = incident.blast_radius
        lines.append("")
        lines.append("## Blast radius")
        lines.append(f"- Upstream assets: {len(br.upstream)}")
        lines.append(f"- Downstream assets: {len(br.downstream)}")
        if br.affected_ml_models:
            lines.append(f"- ML models affected: {', '.join(m.urn for m in br.affected_ml_models)}")
        if br.affected_dashboards:
            lines.append(f"- Dashboards affected: {', '.join(d.urn for d in br.affected_dashboards)}")
        if br.affected_pipelines:
            lines.append(f"- Pipelines affected: {', '.join(p.urn for p in br.affected_pipelines)}")
    if incident.notified_owners:
        lines.append("")
        lines.append("## Notified")
        lines.append(", ".join(incident.notified_owners))
    if incident.slack_message_ts:
        lines.append("")
        lines.append("## Slack notification")
        lines.append(f"Message timestamp: `{incident.slack_message_ts}`")
    lines.append("")
    lines.append("---")
    lines.append(
        "*Generated automatically by [LineagePulse](https://github.com/Donyemiight/lineagepulse) — "
        "DataHub Agent Hackathon submission.*"
    )
    return "\n".join(lines)
