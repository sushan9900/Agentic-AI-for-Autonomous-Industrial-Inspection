"""Pydantic v2 schemas for Adaptive Recommendations (Phase 7E)."""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


RecommendationTypeLiteral = Literal[
    "HIGHER_REVIEW_PRIORITY",
    "REQUEST_ADDITIONAL_EVIDENCE",
    "REPEAT_INSPECTION",
    "REQUIRE_EXPERT_REVIEW",
    "WATCH_FOR_RECURRING_DEFECT",
]

AdvisoryPriorityLiteral = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class AdaptiveRecommendation(BaseModel):
    """
    Explainable, deterministic advisory recommendation synthesized from human review learning.
    Strictly advisory: does NOT authorize maintenance, dispatch technicians, or alter authoritative risk.
    """
    recommendation_id: str = Field(..., description="Unique recommendation ID (rec-xxx)")
    asset_id: Optional[str] = Field(default=None, description="Target asset ID if asset-scoped")
    component_id: Optional[str] = Field(default=None, description="Target component ID if component-scoped")

    recommendation_type: RecommendationTypeLiteral = Field(..., description="Standardized recommendation category")
    reason: str = Field(..., description="Evidence-grounded rationale for the advisory recommendation")

    supporting_pattern_ids: List[str] = Field(default_factory=list, description="IDs of supporting detected error patterns")
    supporting_inspection_ids: List[str] = Field(default_factory=list, description="IDs of past inspections supporting recommendation")

    advisory_priority: AdvisoryPriorityLiteral = Field(default="MEDIUM", description="Advisory urgency level")
    suggested_score_adjustment: int = Field(default=0, ge=-10, le=15, description="Advisory review priority point adjustment (-10 to +15)")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    authoritative: bool = Field(default=False, description="Strict safety invariant: recommendations are never authoritative")

    model_config = ConfigDict(extra="forbid")


class AdaptiveRecommendationsResponse(BaseModel):
    """Response envelope for active adaptive recommendations."""
    total_recommendations: int = Field(..., ge=0)
    recommendations: List[AdaptiveRecommendation] = Field(default_factory=list)
    methodology_version: str = Field(default="1.0")
    safety_notice: str = Field(
        default="Adaptive recommendations are advisory-only and do not modify authoritative inspection decisions or execute field actions."
    )

    model_config = ConfigDict(extra="forbid")
