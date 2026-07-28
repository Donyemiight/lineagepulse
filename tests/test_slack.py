"""Tests for the Slack notifier."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lineagepulse.config import Settings
from lineagepulse.models import (
    AssetRef,
    BlastRadius,
    Incident,
    IncidentKind,
    IncidentReport,
    IncidentSeverity,
)
from lineagepulse.slack import post_incident, render_blocks


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
        title="Test incident",
        summary="x is broken",
        asset=asset,
        blast_radius=BlastRadius(
            root=asset,
            downstream=[AssetRef(urn="urn:li:dataset:(snowflake,y,PROD)")],
        ),
    )


def _report() -> IncidentReport:
    return IncidentReport(
        title="Test incident",
        executive_summary="x is broken",
        root_cause_hypothesis="Network blip",
        suggested_fix="Retry the upstream pipeline",
        blast_radius_summary="1 downstream dataset",
        severity_rationale="Direct failure on a critical asset",
        recommended_actions=["Re-run pipeline", "Verify with the on-call"],
    )


def test_render_blocks_has_required_structure():
    settings = Settings(dry_run=True)
    blocks = render_blocks(_incident(), _report(), settings)
    assert "blocks" in blocks
    assert "text" in blocks
    assert isinstance(blocks["blocks"], list)
    assert len(blocks["blocks"]) >= 4
    # First block should be a header
    assert blocks["blocks"][0]["type"] == "header"
    # Should include the recommended actions
    assert any(
        "Recommended actions" in (b.get("text", {}) or {}).get("text", "")
        for b in blocks["blocks"]
    )


def test_render_blocks_includes_ml_in_blast_radius():
    settings = Settings(dry_run=True)
    inc = _incident()
    inc.blast_radius.affected_ml_models = [
        AssetRef(urn="urn:li:mlModel:(mlflow,model,PROD)", name="model")
    ]
    inc.blast_radius.affected_dashboards = [
        AssetRef(urn="urn:li:dashboard:(looker,dash,PROD)", name="dash")
    ]
    blocks = render_blocks(inc, _report(), settings)
    text_blob = json.dumps(blocks)
    assert "ML" in text_blob or "model" in text_blob
    assert "dash" in text_blob or "dashboard" in text_blob


def test_post_incident_dry_run_returns_dry_run_marker():
    settings = Settings(dry_run=True, slack_webhook_url=None)
    result = post_incident(_incident(), _report(), settings)
    assert result is not None
    assert result.startswith("dry-run-")


def test_post_incident_live_calls_requests():
    settings = Settings(dry_run=False, slack_webhook_url="https://hooks.slack.com/test")
    with patch("lineagepulse.slack.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ts": "12345.6789"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        result = post_incident(_incident(), _report(), settings)
    assert result == "12345.6789"
    mock_post.assert_called_once()


def test_post_incident_no_webhook_returns_none():
    settings = Settings(dry_run=False, slack_webhook_url=None)
    result = post_incident(_incident(), _report(), settings)
    assert result is None
