"""Pydantic v2 schemas for Inspection Timing Recommendations (Phase 8D)."""

from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.inspection_task import TimingWindow


class TimingRecommendation(BaseModel):
    """
    Explainable, deterministic timing window recommendation for an inspection task.
    Strictly advisory: authoritative = False.
    """
    timing_window: TimingWindow = Field(..., description="Recommended execution window")
    urgency: str = Field(..., description="Urgency classification: CRITICAL, HIGH, MEDIUM, LOW")
    rationale: str = Field(..., description="Deterministic engineering rationale for timing window")
    supporting_factors: List[str] = Field(default_factory=list, description="Explicit contributing factors")
    authoritative: bool = Field(default=False, description="Strict safety invariant: timing recommendations are never authoritative")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")
