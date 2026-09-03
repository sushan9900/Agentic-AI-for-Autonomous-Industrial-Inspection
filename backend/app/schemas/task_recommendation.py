"""Pydantic v2 schemas for Inspection Task Recommendations (Phase 8C)."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.inspection_task import TimingWindow


class RecommendationType(str, Enum):
    """Actionable recommendation categories for industrial inspection coordination."""
    CREATE_INSPECTION = "CREATE_INSPECTION"
    REVIEW_EXISTING_INSPECTION = "REVIEW_EXISTING_INSPECTION"
    REQUEST_ADDITIONAL_EVIDENCE = "REQUEST_ADDITIONAL_EVIDENCE"
    REPEAT_INSPECTION = "REPEAT_INSPECTION"
    REQUIRE_EXPERT_REVIEW = "REQUIRE_EXPERT_REVIEW"


class RecommendationUrgency(str, Enum):
    """Urgency priority tiers for recommendations."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskRecommendation(BaseModel):
    """
    Explainable, deterministic advisory recommendation for an inspection task.
    Strictly advisory: authoritative = False, human_approval_required = True.
    """
    recommendation_id: str = Field(..., description="Unique recommendation identifier (rec-task-xxx)")
    asset_id: str = Field(..., description="Target industrial asset ID")
    component_id: Optional[str] = Field(default=None, description="Target component ID")
    inspection_id: Optional[str] = Field(default=None, description="Associated existing inspection ID if applicable")

    recommendation_type: RecommendationType = Field(..., description="Type of orchestrated inspection action recommended")
    urgency: RecommendationUrgency = Field(default=RecommendationUrgency.MEDIUM)
    timing_window: TimingWindow = Field(default=TimingWindow.ROUTINE)

    reason: str = Field(..., description="Detailed engineering rationale synthesized from inspection intelligence")
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    supporting_inspection_ids: List[str] = Field(default_factory=list)

    authoritative: bool = Field(default=False, description="Strict safety invariant: recommendations are never authoritative")
    human_approval_required: bool = Field(default=True, description="Strict safety gate: human approval mandatory")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


class TaskRecommendationsResponse(BaseModel):
    """Response envelope for active inspection task recommendations."""
    total_recommendations: int
    recommendations: List[TaskRecommendation] = Field(default_factory=list)
    methodology_version: str = Field(default="1.0")
    safety_notice: str = Field(
        default="Inspection task recommendations are advisory-only and require authorized human engineering approval before execution."
    )

    model_config = ConfigDict(extra="forbid")
