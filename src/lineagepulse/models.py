"""Data models for LineagePulse.

The agent is built around three first-class objects:

- ``Incident`` — a detected problem on a specific asset
- ``BlastRadius`` — the upstream + downstream impact graph of that asset
- ``IncidentReport`` — the LLM-authored root-cause narrative + fix plan

These are intentionally simple Pydantic models so they are easy to log,
serialize to JSON for the ``examples/`` folder, and write back to DataHub
as Documents.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class IncidentSeverity(str, Enum):
    """How bad is this?"""

    LOW = "low"  # cosmetic, e.g. missing description
    MEDIUM = "medium"  # degraded freshness, soft assertion
    HIGH = "high"  # hard failure, downstream impact
    CRITICAL = "critical"  # model in production affected


class IncidentStatus(str, Enum):
    """Lifecycle states."""

    DETECTED = "detected"
    INVESTIGATING = "investigating"
    NOTIFIED = "notified"
    DOCUMENTED = "documented"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"  # de-duped or under maintenance


class IncidentKind(str, Enum):
    """What kind of thing went wrong?"""

    ASSERTION_FAILURE = "assertion_failure"
    SCHEMA_CHANGE = "schema_change"
    FRESHNESS_VIOLATION = "freshness_violation"
    DEPRECATION = "deprecation"
    GLOSSARY_GAP = "glossary_gap"
    ML_DRIFT = "ml_drift"
    LINEAGE_BREAK = "lineage_break"


class AssetRef(BaseModel):
    """Pointer to a DataHub entity (dataset, dashboard, ML model, ...)."""

    urn: str
    type: str = "dataset"  # dataset | dashboard | mlModel | chart | dataJob
    platform: str | None = None
    name: str | None = None
    owners: list[str] = Field(default_factory=list)
    domain: str | None = None


class BlastRadius(BaseModel):
    """The graph around the failing asset."""

    root: AssetRef
    upstream: list[AssetRef] = Field(default_factory=list)
    downstream: list[AssetRef] = Field(default_factory=list)
    affected_ml_models: list[AssetRef] = Field(default_factory=list)
    affected_dashboards: list[AssetRef] = Field(default_factory=list)
    affected_pipelines: list[AssetRef] = Field(default_factory=list)

    @property
    def total_impacted(self) -> int:
        return (
            len(self.upstream)
            + len(self.downstream)
            + len(self.affected_ml_models)
            + len(self.affected_dashboards)
            + len(self.affected_pipelines)
        )


class Incident(BaseModel):
    """A single detected problem."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: IncidentKind
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.DETECTED
    title: str
    summary: str
    asset: AssetRef
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "datahub"  # where the signal came from
    source_id: str | None = None  # e.g. assertion urn
    raw_signal: dict = Field(default_factory=dict)
    blast_radius: BlastRadius | None = None
    root_cause: str | None = None
    suggested_fix: str | None = None
    notified_owners: list[str] = Field(default_factory=list)
    slack_message_ts: str | None = None
    datahub_document_urn: str | None = None


class IncidentReport(BaseModel):
    """LLM-authored explanation of the incident."""

    title: str
    executive_summary: str
    root_cause_hypothesis: str
    suggested_fix: str
    blast_radius_summary: str
    severity_rationale: str
    recommended_actions: list[str] = Field(default_factory=list)


__all__ = [
    "AssetRef",
    "BlastRadius",
    "Incident",
    "IncidentKind",
    "IncidentReport",
    "IncidentSeverity",
    "IncidentStatus",
]
