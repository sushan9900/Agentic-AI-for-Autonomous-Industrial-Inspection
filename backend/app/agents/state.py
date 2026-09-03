"""Agent state contract defining the full inspection decision lifecycle (Phase 3B)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.agents.trace import TraceEvent


class AgentInspectionState(BaseModel):
    """Complete internal state representation for the autonomous inspection decision agent."""
    inspection_id: str = Field(..., description="Unique inspection transaction identifier")
    asset_id: str = Field(..., description="Target industrial asset identifier")
    component_id: Optional[str] = Field(default=None, description="Optional target component identifier")

    # 1. Perception Evidence
    evidence: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured VisionEvidence v1.0 payload"
    )

    # 2. Retrieved Relational Context
    asset_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Asset specifications and component breakdown"
    )
    maintenance_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Historical maintenance records"
    )
    severity_thresholds: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Triggered or applicable project engineering rules"
    )
    similar_incidents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Similar failure incidents and failure modes"
    )
    historical_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured historical inspection intelligence, similar past inspections, and risk trend (Phase 6A)"
    )
    inspection_trends: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured multi-inspection trend analysis across time (Phase 6B)"
    )
    investigation_plan: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured decision-support investigation plan (Phase 6C)"
    )

    # 3. Deterministic Risk & Policy Assessment
    risk_assessment: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Deterministic risk score and explainable factor breakdown"
    )
    operational_decision: Optional[str] = Field(
        default=None,
        description="Deterministic decision outcome (e.g. URGENT_ENGINEERING_REVIEW, PLAN_MAINTENANCE)"
    )
    decision_rationale: Optional[str] = Field(
        default=None,
        description="Summary rationale for operational decision"
    )

    # 4. Synthesized Work Order Recommendation
    work_order: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Draft maintenance work order recommendation"
    )

    # 5. Observable Trace & Observability
    trace: List[TraceEvent] = Field(
        default_factory=list,
        description="Chronological operational step trace"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages logged during execution"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Engineering or quality warnings"
    )
    evidence_gaps: List[str] = Field(
        default_factory=list,
        description="Missing data points or unavailable telemetry"
    )
    final_status: str = Field(
        default="PENDING_HUMAN_REVIEW",
        description="Overall lifecycle state: PENDING_HUMAN_REVIEW, COMPLETED, FAILED"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


# Alias for backward compatibility if needed
AgentState = AgentInspectionState
