"""Pydantic v2 schemas for Prediction vs Outcome Learning Analysis and Error Patterns (Phase 7C/7D)."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class PredictionOutcomeComparison(BaseModel):
    """Detailed itemized comparison between AI prediction and confirmed review outcome."""
    inspection_id: str
    asset_id: str
    component_id: Optional[str] = None

    defect_agreement: bool = Field(..., description="Whether AI and reviewer agreed on defect presence")
    severity_agreement: bool = Field(..., description="Whether AI and reviewer agreed on physical severity")
    risk_band_agreement: bool = Field(..., description="Whether AI and reviewer agreed on overall risk band")
    action_agreement: bool = Field(..., description="Whether AI operational action was accepted without modification")

    is_false_positive: bool = Field(..., description="AI detected defect, but reviewer confirmed defect absent")
    is_false_negative: bool = Field(..., description="AI missed defect, but reviewer confirmed defect present")

    severity_delta: int = Field(..., description="Numeric difference: positive = AI overestimated, negative = AI underestimated")
    ai_severity: str
    confirmed_severity: str
    ai_risk_score: int
    review_status: str

    model_config = ConfigDict(extra="forbid")


class LearningMetricsSummary(BaseModel):
    """Deterministic aggregate agreement, error, and correction metrics across reviewed inspections."""
    total_reviewed: int = Field(..., ge=0, description="Total number of finalized human review outcomes")
    defect_agreement_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of defect presence agreements")
    severity_agreement_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of severity classifications agreed")
    risk_band_agreement_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of risk bands agreed")
    action_agreement_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of operational actions accepted")
    overall_reviewer_agreement_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of uncorrected approvals")

    false_positive_count: int = Field(..., ge=0)
    false_positive_rate: float = Field(..., ge=0.0, le=1.0)
    false_negative_count: int = Field(..., ge=0)
    false_negative_rate: float = Field(..., ge=0.0, le=1.0)

    correction_count: int = Field(..., ge=0)
    correction_rate: float = Field(..., ge=0.0, le=1.0)

    severity_overestimation_count: int = Field(..., ge=0)
    severity_underestimation_count: int = Field(..., ge=0)

    methodology_version: str = Field(default="1.0", description="Metrics calculation standard")

    model_config = ConfigDict(extra="forbid")


class DetectedPattern(BaseModel):
    """Deterministic recurring discrepancy pattern identified across historical review outcomes."""
    pattern_id: str = Field(..., description="Unique pattern identifier")
    pattern_type: Literal[
        "REPEATED_FALSE_POSITIVES",
        "REPEATED_FALSE_NEGATIVES",
        "RECURRING_SEVERITY_OVERESTIMATION",
        "RECURRING_SEVERITY_UNDERESTIMATION",
        "REPEATED_ACTION_DISAGREEMENT",
    ]
    asset_id: Optional[str] = None
    component_id: Optional[str] = None
    occurrence_count: int = Field(..., ge=2, description="Number of observed recurring discrepancies")
    affected_inspection_ids: List[str] = Field(default_factory=list)
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    explanation: str = Field(..., description="Clear evidence-grounded explanation of the error pattern")
    first_seen: datetime
    last_seen: datetime

    model_config = ConfigDict(extra="forbid")


class LearningPatternsResponse(BaseModel):
    """Response envelope for detected error patterns."""
    total_patterns: int = Field(..., ge=0)
    patterns: List[DetectedPattern] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
