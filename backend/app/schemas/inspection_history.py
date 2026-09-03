"""Pydantic v2 schemas for Inspection Memory & Historical Intelligence (Phase 6A)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


RiskTrendLiteral = Literal["STABLE", "INCREASING", "DECREASING", "INSUFFICIENT_HISTORY"]


class HistoricalInspectionRecord(BaseModel):
    """Normalized structured representation of a historical inspection record."""
    inspection_id: str = Field(..., description="Unique historical inspection identifier")
    asset_id: str = Field(..., description="Associated industrial asset identifier")
    component_id: Optional[str] = Field(default=None, description="Associated inspectable component identifier")
    inspection_timestamp: datetime = Field(..., description="Timestamp of the historical inspection")
    defect_type: Optional[str] = Field(default=None, description="Primary detected defect classification")
    severity: Optional[str] = Field(default=None, description="Perception or engineering severity rating")
    risk_score: Optional[int] = Field(default=None, ge=0, le=100, description="Historical authoritative risk score if assessed")
    authoritative_action: Optional[str] = Field(default=None, description="Historical authoritative operational decision")
    human_review_status: Optional[str] = Field(default=None, description="Lifecycle review state: PENDING_HUMAN_REVIEW, APPROVED, REJECTED")
    source_record_id: str = Field(..., description="Primary key or traceable database record identifier")
    similarity_reason: str = Field(..., description="Deterministic rationale for why this record was retrieved")

    model_config = ConfigDict(extra="forbid")


class HistoricalSummary(BaseModel):
    """Deterministic longitudinal summary of historical inspection track record."""
    total_previous_inspections: int = Field(default=0, ge=0, description="Total count of prior inspections on this asset")
    same_component_inspections: int = Field(default=0, ge=0, description="Total count of prior inspections on this specific component")
    previous_critical_events: int = Field(default=0, ge=0, description="Count of prior inspections with critical risk or urgent action")
    recurring_defect_detected: bool = Field(default=False, description="True if identical defect type was previously detected on asset/component")
    latest_previous_risk_score: Optional[int] = Field(default=None, ge=0, le=100, description="Risk score from the most recent prior decision")
    risk_trend: RiskTrendLiteral = Field(
        default="INSUFFICIENT_HISTORY",
        description="Deterministic risk trend: STABLE, INCREASING, DECREASING, or INSUFFICIENT_HISTORY"
    )
    trend_explanation: str = Field(
        default="Fewer than 2 valid historical risk assessments exist for trend analysis.",
        description="Transparent mathematical explanation of the computed risk trend"
    )

    model_config = ConfigDict(extra="forbid")


class HistoricalInspectionContext(BaseModel):
    """Master structured context payload consumed by the Inspection Decision Agent."""
    has_history: bool = Field(default=False, description="True if any valid prior inspection records were located")
    asset_id: str = Field(..., description="Target industrial asset identifier")
    component_id: Optional[str] = Field(default=None, description="Target component identifier if specified")
    summary: HistoricalSummary = Field(default_factory=HistoricalSummary, description="Deterministic track record summary")
    recent_inspections: List[HistoricalInspectionRecord] = Field(
        default_factory=list,
        description="Chronologically sorted recent inspections for this asset"
    )
    similar_inspections: List[HistoricalInspectionRecord] = Field(
        default_factory=list,
        description="Inspections matching component, defect type, or severity"
    )
    previous_decisions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Historical agent decision and human review records"
    )
    retrieval_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provenance of the retrieval query (timestamps, record counts, query time)"
    )

    model_config = ConfigDict(extra="forbid")
