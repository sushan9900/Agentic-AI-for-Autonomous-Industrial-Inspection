"""Pydantic v2 schemas for Agentic Inspection Prioritization & Scheduling (Phase 6D)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


PriorityClassLiteral = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class InspectionPriorityItem(BaseModel):
    """
    Transparent, deterministic review prioritization item for an inspection awaiting human review.
    Clearly distinguishes authoritative risk/decision from derived review priority.
    """
    inspection_id: str = Field(..., description="Unique inspection transaction identifier")
    decision_id: str = Field(..., description="Associated authoritative agent decision ID")
    asset_id: str = Field(..., description="Target industrial asset ID")
    component_id: Optional[str] = Field(default=None, description="Inspectable component ID")

    # Derived Review Priority (Non-Authoritative)
    priority_rank: int = Field(..., ge=1, description="Deterministic 1-indexed queue rank for human review")
    priority_class: PriorityClassLiteral = Field(..., description="Human review urgency class: CRITICAL, HIGH, MEDIUM, LOW")
    priority_score: int = Field(..., ge=0, le=100, description="Deterministic derived review priority score (0-100 pts)")

    # Authoritative Inspection Baseline (Immutable)
    authoritative_risk_score: int = Field(..., ge=0, le=100, description="Authoritative risk score from DecisionPolicyEngine (0-100)")
    severity: str = Field(..., description="Authoritative physical defect severity")
    operational_action: str = Field(..., description="Authoritative operational action (e.g. URGENT_ENGINEERING_REVIEW)")
    review_status: str = Field(..., description="Current human review state (e.g. PENDING_HUMAN_REVIEW)")
    human_review_required: bool = Field(default=True, description="Strict safety gate: human review requirement")

    # Supporting Multi-Phase Intelligence
    investigation_priority: Optional[str] = Field(default=None, description="Diagnostic investigation priority tier (Phase 6C)")
    deterioration_status: Optional[str] = Field(default=None, description="Multi-inspection deterioration trend (Phase 6B)")
    recurrence_pattern: Optional[str] = Field(default=None, description="Historical defect recurrence classification (Phase 6B)")
    evidence_sufficiency: Optional[str] = Field(default=None, description="Historical evidence sufficiency (Phase 6A/6B)")
    investigation_plan_id: Optional[str] = Field(default=None, description="Associated investigation plan ID (Phase 6C)")
    diagnostic_steps_count: int = Field(default=0, ge=0, description="Number of diagnostic steps in investigation plan")
    information_gaps_count: int = Field(default=0, ge=0, description="Number of identified unobserved information gaps")
    pending_age_hours: Optional[float] = Field(default=None, ge=0.0, description="Hours elapsed since decision creation")

    # Epistemic Transparency
    rationale: str = Field(..., description="Explainable engineering rationale for the derived review priority")
    contributing_factors: List[str] = Field(default_factory=list, description="Explicit factor breakdown with point contributions")
    source_inspection_ids: List[str] = Field(default_factory=list, description="Traceable past inspections contributing to context")

    # Metadata & Safety Invariant
    generated_by: str = Field(default="deterministic_prioritization_engine_v1", description="Prioritization engine identifier")
    authoritative: bool = Field(default=False, description="Strict safety invariant: review priorities are never authoritative")

    model_config = ConfigDict(extra="forbid")


class InspectionPriorityQueue(BaseModel):
    """
    Ordered queue of pending inspections prioritized for human engineering review.
    Recommends review order without performing autonomous maintenance or control.
    """
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of queue generation")
    total_pending: int = Field(..., ge=0, description="Total count of pending inspections in queue")
    items: List[InspectionPriorityItem] = Field(default_factory=list, description="Ranked list of inspection priority items")
    methodology_version: str = Field(default="1.0", description="Prioritization scoring methodology version")
    safety_notice: str = Field(
        default="This queue recommends human review order only. It does not authorize or execute maintenance.",
        description="Mandatory safety boundary notice"
    )

    model_config = ConfigDict(extra="forbid")
