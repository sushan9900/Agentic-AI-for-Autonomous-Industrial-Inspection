"""Tools package exports (Phase 2B + Phase 3B)."""

from backend.app.tools.asset_context import (
    AssetContextInput,
    AssetContextOutput,
    GetAssetContextTool,
    get_asset_context_tool,
)
from backend.app.tools.base import BaseAgentTool
from backend.app.tools.component_context import (
    ComponentContextInput,
    ComponentContextOutput,
    GetComponentContextTool,
)
from backend.app.tools.maintenance_history import (
    GetMaintenanceHistoryTool,
    MaintenanceHistoryInput,
    MaintenanceHistoryOutput,
    get_maintenance_history_tool,
)
from backend.app.tools.risk_scoring import (
    CalculateRiskScoreTool,
    RiskScoreInput,
    RiskScoreOutput,
    calculate_risk_score_tool,
)
from backend.app.tools.severity_thresholds import (
    GetSeverityThresholdsTool,
    SeverityThresholdInput,
    SeverityThresholdOutput,
    SeverityThresholdRule,
    get_severity_thresholds_tool,
)
from backend.app.tools.similar_incidents import (
    CheckSimilarIncidentsTool,
    SimilarIncidentsInput,
    SimilarIncidentsOutput,
    SimilarIncidentSummary,
    check_similar_incidents_tool,
)

__all__ = [
    "BaseAgentTool",
    # Tool 1: Asset Context
    "GetAssetContextTool",
    "get_asset_context_tool",
    "AssetContextInput",
    "AssetContextOutput",
    # Tool 2: Maintenance History
    "GetMaintenanceHistoryTool",
    "get_maintenance_history_tool",
    "MaintenanceHistoryInput",
    "MaintenanceHistoryOutput",
    # Tool 3: Severity Thresholds
    "GetSeverityThresholdsTool",
    "get_severity_thresholds_tool",
    "SeverityThresholdInput",
    "SeverityThresholdOutput",
    "SeverityThresholdRule",
    # Tool 4: Similar Incidents
    "CheckSimilarIncidentsTool",
    "check_similar_incidents_tool",
    "SimilarIncidentsInput",
    "SimilarIncidentsOutput",
    "SimilarIncidentSummary",
    # Tool 5: Risk Scoring
    "CalculateRiskScoreTool",
    "calculate_risk_score_tool",
    "RiskScoreInput",
    "RiskScoreOutput",
    # Legacy / Component Context
    "GetComponentContextTool",
    "ComponentContextInput",
    "ComponentContextOutput",
]
