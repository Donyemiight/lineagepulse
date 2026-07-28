"""Unit tests for the LineagePulse DataHub client.

These tests verify the wrapper around the DataHub Agent Context Kit
without requiring a live DataHub instance. We mock the LangChain tools
to assert the right tool is called with the right arguments.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lineagepulse.config import Settings
from lineagepulse.datahub_client import DataHubClient
from lineagepulse.models import AssetRef, Incident, IncidentKind, IncidentSeverity


def _mock_tool(name: str, return_value):
    t = MagicMock()
    t.name = name
    t.invoke = MagicMock(return_value=return_value)
    return t


@pytest.fixture
def mock_client():
    """Build a DataHubClient with mocked Agent Context Kit tools."""
    settings = Settings(dry_run=True, datahub_mutations_enabled=True)
    client = DataHubClient(settings)

    read_tools = {
        "search": _mock_tool("search", [{"urn": "urn:li:dataset:(snowflake,x,PROD)"}]),
        "get_entities": _mock_tool("get_entities", {
            "urn": "urn:li:dataset:(snowflake,taxi_trips,PROD)",
            "name": "taxi_trips",
            "platform": "snowflake",
            "ownership": {"owners": [{"owner": "alice@acme.io"}, {"owner": "bob@acme.io"}]},
            "domain": {"name": "Mobility"},
        }),
        "get_lineage": _mock_tool("get_lineage", [
            {"urn": "urn:li:dataset:(snowflake,downstream,PROD)", "platform": "snowflake"},
            {"urn": "urn:li:mlModel:(mlflow,model,PROD)", "platform": "mlflow"},
        ]),
        "list_schema_fields": _mock_tool("list_schema_fields", [{"path": "id", "type": "int"}]),
        "get_dataset_queries": _mock_tool("get_dataset_queries", []),
        "get_dataset_assertions": _mock_tool("get_dataset_assertions", [
            {"urn": "urn:li:assertion:1", "state": "FAILURE", "message": "Stale", "type": "freshness"}
        ]),
        "search_documents": _mock_tool("search_documents", []),
    }
    write_tools = {
        "save_document": _mock_tool("save_document", {"urn": "urn:li:document:incident-x"}),
        **read_tools,
    }
    client._client = MagicMock()
    client._read_tools = read_tools
    client._write_tools = write_tools
    return client


def test_get_asset_uses_get_entities(mock_client):
    asset = mock_client.get_asset("urn:li:dataset:(snowflake,taxi_trips,PROD)")
    assert asset is not None
    assert asset.name == "taxi_trips"
    assert asset.platform == "snowflake"
    assert "alice@acme.io" in asset.owners
    assert asset.domain == "Mobility"
    mock_client._read_tools["get_entities"].invoke.assert_called_once()


def test_get_lineage_walks_downstream(mock_client):
    blast = mock_client.get_lineage("urn:li:dataset:(snowflake,taxi_trips,PROD)", direction="downstream")
    assert len(blast.downstream) == 2
    assert any(r.type == "mlModel" for r in blast.downstream)
    assert len(blast.affected_ml_models) == 1
    mock_client._read_tools["get_lineage"].invoke.assert_called()


def test_search_calls_search_tool(mock_client):
    results = mock_client.search("freshness", limit=5)
    assert len(results) == 1
    assert "urn" in results[0]
    mock_client._read_tools["search"].invoke.assert_called_once()


def test_write_incident_document_calls_save_document(mock_client):
    settings = Settings(dry_run=False, datahub_mutations_enabled=True)
    client = DataHubClient.__new__(DataHubClient)
    client.settings = settings
    client._client = MagicMock()
    client._read_tools = mock_client._read_tools
    client._write_tools = mock_client._write_tools

    incident = Incident(
        kind=IncidentKind.ASSERTION_FAILURE,
        severity=IncidentSeverity.HIGH,
        title="Test",
        summary="x",
        asset=AssetRef(urn="urn:li:dataset:(snowflake,x,PROD)"),
    )
    urn = client.write_incident_document(incident)
    assert urn is not None
    assert urn.startswith("urn:li:document:incident-")
    assert incident.datahub_document_urn == urn
    mock_client._write_tools["save_document"].invoke.assert_called_once()


def test_dry_run_skips_writeback(mock_client):
    settings = Settings(dry_run=True, datahub_mutations_enabled=True)
    client = DataHubClient.__new__(DataHubClient)
    client.settings = settings
    client._client = MagicMock()
    client._read_tools = mock_client._read_tools
    client._write_tools = mock_client._write_tools
    incident = Incident(
        kind=IncidentKind.ASSERTION_FAILURE,
        severity=IncidentSeverity.HIGH,
        title="t",
        summary="s",
        asset=AssetRef(urn="urn:li:dataset:(snowflake,x,PROD)"),
    )
    assert client.write_incident_document(incident) is None
    mock_client._write_tools["save_document"].invoke.assert_not_called()


def test_mutations_disabled_skips_writeback(mock_client):
    settings = Settings(dry_run=False, datahub_mutations_enabled=False)
    client = DataHubClient.__new__(DataHubClient)
    client.settings = settings
    client._client = MagicMock()
    client._read_tools = mock_client._read_tools
    client._write_tools = mock_client._write_tools
    incident = Incident(
        kind=IncidentKind.ASSERTION_FAILURE,
        severity=IncidentSeverity.HIGH,
        title="t",
        summary="s",
        asset=AssetRef(urn="urn:li:dataset:(snowflake,x,PROD)"),
    )
    assert client.write_incident_document(incident) is None
    mock_client._write_tools["save_document"].invoke.assert_not_called()


def test_fetch_failing_assertions_returns_incidents(mock_client):
    incidents = mock_client.fetch_failing_assertions()
    assert len(incidents) >= 1
    assert incidents[0].kind in (IncidentKind.ASSERTION_FAILURE, IncidentKind.FRESHNESS_VIOLATION)
    assert incidents[0].severity == IncidentSeverity.HIGH


def test_available_returns_true_when_initialized(mock_client):
    assert mock_client.available is True


def test_tools_summary(mock_client):
    summary = mock_client.tools_summary
    assert "search" in summary["read"]
    assert "save_document" in summary["write"]
