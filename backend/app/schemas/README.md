# Schemas Directory (`backend/app/schemas`)

Pydantic v2 domain schemas and data contracts across all platform subsystems.

## Key Schemas
* **`agent_decision.py`**: `AgentInspectionDecision`, `WorkOrderRecommendation`, `AgentInspectRequest`.
* **`analytics.py`**: `DefectRecordRead`, `DefectTrendAnalysis`, `AssetRiskSnapshot`, `AssetTimelineResponse`.
* **`asset.py`**: `AssetCreate`, `AssetUpdate`, `AssetRead`, `AssetDetailRead`, `AssetSummaryRead`.
* **`review.py`**: `InspectionReviewRead`, `ReviewAuditLogRead`, `ReviewActionRequest`.
* **`decision.py`**: `InspectionDecision`, `RuleEvaluation`.
* **`context.py`**: `HistoricalContext`, `ComponentContext`.
