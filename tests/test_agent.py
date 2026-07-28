"""Tests for the LineagePulse agent orchestration."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lineagepulse.agent import (
    detect_incidents,
    handle_incident,
    investigate_incident,
    respond_to_incident,
)
from lineagepulse.config import Settings
from lineagepulse.datahub_client import DataHubClient
from lineagepulse.models import (
    AssetRef,
    BlastRadius,
    Incident,
    IncidentKind,
    IncidentSeverity,
)


def _incident() -> Incident:
    asset = AssetRef(
        urn="urn:li:dataset:(snowflake,x,PROD)",
        name="x",
        platform="snowflake",
        owners=["alice@acme.io"],
        domain="Finance",
    )
    return Incident(
        kind=IncidentKind.ASSERTION_FAILURE,
        severity=IncidentSeverity.HIGH,
        title="Test",
        summary="x is broken",
        asset=asset,
        raw_signal={"assertion_urn": "urn:li:assertion:1", "state": "FAILURE"},
    )


def _mock_client_with_ml_in_blast() -> DataHubClient:
    settings = Settings(dry_run=True, datahub_mutations_enabled=False)
    client = DataHubClient.__new__(DataHubClient)
    client.settings = settings
    client._client = MagicMock()
    client._read_tools = {}
    client._write_tools = {}

    asset = _incident().asset
    # Mock the relevant methods
    client.get_asset = MagicMock(return_value=asset)
    client.get_lineage = MagicMock(
        return_value=BlastRadius(
            root=asset,
            downstream=[
                AssetRef(urn="urn:li:dataset:(snowflake,down,PROD)", name="down", platform="snowflake"),
                AssetRef(urn="urn:li:mlModel:(mlflow,model,PROD)", name="model", platform="mlflow"),
            ],
            affected_ml_models=[
                AssetRef(urn="urn:li:mlModel:(mlflow,model,PROD)", name="model", platform="mlflow"),
            ],
        )
    )
    client.write_incident_document = MagicMock(return_value=None)
    return client


def test_investigate_bumps_severity_when_ml_in_blast():
    settings = Settings(dry_run=True)
    client = _mock_client_with_ml_in_blast()
    inc = _incident()
    inc = investigate_incident(inc, client, settings)
    assert inc.severity == IncidentSeverity.CRITICAL
    assert inc.blast_radius is not None
    assert len(inc.blast_radius.affected_ml_models) == 1


def test_respond_writes_document_and_dry_runs_slack():
    settings = Settings(dry_run=True, slack_webhook_url=None)
    client = _mock_client_with_ml_in_blast()
    inc = _incident()
    inc = investigate_incident(inc, client, settings)
    inc = respond_to_incident(inc, client, settings)
    client.write_incident_document.assert_called_once()
    # In dry-run, slack returns a marker, not a real ts
    assert inc.slack_message_ts is not None
    assert inc.slack_message_ts.startswith("dry-run-")


def test_handle_incident_full_loop():
    settings = Settings(dry_run=True)
    client = _mock_client_with_ml_in_blast()
    inc = handle_incident(_incident(), client, settings)
    assert inc.severity == IncidentSeverity.CRITICAL
    assert inc.blast_radius is not None
    assert inc.root_cause is not None  # heuristic sets this


def test_detect_incidents_calls_polling():
    settings = Settings(dry_run=True)
    client = DataHubClient.__new__(DataHubClient)
    client.settings = settings
    client._client = MagicMock()
    client._read_tools = {}
    client._write_tools = {}
    client.fetch_failing_assertions = MagicMock(return_value=[_incident()])
    result = detect_incidents(client, settings)
    assert len(result) == 1
    client.fetch_failing_assertions.assert_called_once()
