"""LineagePulse — DataHub Agent Hackathon submission.

Multi-agent incident response on top of DataHub's context graph.

Public surface:
    - ``run_once``: poll DataHub for one incident cycle
    - ``run_daemon``: long-running agent loop
    - ``demo``: simulate a failing assertion and watch the agent respond
"""

from lineagepulse.cli import main
from lineagepulse.config import Settings, get_settings
from lineagepulse.models import BlastRadius, Incident, IncidentSeverity, IncidentStatus

__version__ = "0.1.0"
__all__ = [
    "BlastRadius",
    "Incident",
    "IncidentSeverity",
    "IncidentStatus",
    "Settings",
    "get_settings",
    "main",
]
