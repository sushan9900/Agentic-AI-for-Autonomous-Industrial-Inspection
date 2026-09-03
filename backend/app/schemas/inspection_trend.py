"""Pydantic v2 schemas for Multi-Inspection Trend Analysis (Phase 6B)."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


ProgressionTrendLiteral = Literal["INCREASING", "STABLE", "DECREASING", "INSUFFICIENT_HISTORY"]
RecurrencePatternLiteral = Literal["NO_RECURRENCE", "RECURRENT", "PERSISTENT", "INSUFFICIENT_HISTORY"]
FrequencyTrendLiteral = Literal["FREQUENCY_INCREASING", "FREQUENCY_STABLE", "FREQUENCY_DECREASING", "INSUFFICIENT_HISTORY"]
DeteriorationStatusLiteral = Literal["DETERIORATING", "STABLE", "IMPROVING", "RECURRENT_RISK", "INSUFFICIENT_HISTORY"]
EvidenceSufficiencyLiteral = Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT"]


class DefectObservationPoint(BaseModel):
    """Deterministic defect metric observation at a specific historical point in time."""
    timestamp: datetime = Field(..., description="Timestamp of the inspection")
    inspection_id: str = Field(..., description="Traceable inspection identifier")
    defect_type: Optional[str] = Field(default=None, description="Primary detected defect classification")
    defect_count: int = Field(default=0, ge=0, description="Number of defects detected")
    affected_area_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Surface area affected")
    crack_length_pixels: Optional[float] = Field(default=None, ge=0.0, description="Estimated crack length in pixels")
    source_record_id: str = Field(..., description="Traceable database record ID")

    model_config = ConfigDict(extra="forbid")


class SeverityObservationPoint(BaseModel):
    """Categorical and ordinal severity observation at a historical inspection."""
    timestamp: datetime = Field(..., description="Timestamp of the inspection")
    inspection_id: str = Field(..., description="Traceable inspection identifier")
    severity: str = Field(..., description="Reported severity: LOW, MEDIUM, HIGH, CRITICAL")
    severity_rank: int = Field(..., ge=1, le=4, description="Ordinal rank: LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4")
    source_record_id: str = Field(..., description="Traceable database record ID")

    model_config = ConfigDict(extra="forbid")


class RiskScoreObservationPoint(BaseModel):
    """Authoritative risk score assessment observation at a historical inspection."""
    timestamp: datetime = Field(..., description="Timestamp of the inspection decision")
    inspection_id: str = Field(..., description="Traceable inspection identifier")
    risk_score: int = Field(..., ge=0, le=100, description="Authoritative risk score (0-100)")
    risk_level: str = Field(..., description="Authoritative risk tier band: LOW, MEDIUM, HIGH, CRITICAL")
    source_record_id: str = Field(..., description="Traceable database record ID")

    model_config = ConfigDict(extra="forbid")


class InspectionIntervalPoint(BaseModel):
    """Interval in days between consecutive chronological inspections."""
    from_inspection_id: str = Field(..., description="Earlier inspection identifier")
    to_inspection_id: str = Field(..., description="Later inspection identifier")
    interval_days: float = Field(..., ge=0.0, description="Elapsed duration in days")

    model_config = ConfigDict(extra="forbid")


class InspectionTrendAnalysis(BaseModel):
    """Master structured container for multi-inspection trend analysis across time."""
    asset_id: str = Field(..., description="Target industrial asset identifier")
    component_id: Optional[str] = Field(default=None, description="Target component identifier if specified")

    # 1. Temporal Analysis Window
    inspection_count: int = Field(default=0, ge=0, description="Total valid historical inspections analyzed")
    earliest_inspection: Optional[str] = Field(default=None, description="Earliest inspection identifier")
    latest_inspection: Optional[str] = Field(default=None, description="Latest inspection identifier")
    analysis_window_days: Optional[float] = Field(default=None, ge=0.0, description="Total days spanning earliest to latest inspection")

    # 2. Chronological Time Series
    defect_series: List[DefectObservationPoint] = Field(default_factory=list, description="Chronological defect observations")
    severity_series: List[SeverityObservationPoint] = Field(default_factory=list, description="Chronological severity observations")
    risk_series: List[RiskScoreObservationPoint] = Field(default_factory=list, description="Chronological authoritative risk scores")
    interval_series: List[InspectionIntervalPoint] = Field(default_factory=list, description="Intervals between consecutive inspections")

    # 3. Frequency Metrics
    average_interval_days: Optional[float] = Field(default=None, ge=0.0, description="Mean interval in days between inspections")
    minimum_interval_days: Optional[float] = Field(default=None, ge=0.0, description="Minimum interval in days")
    maximum_interval_days: Optional[float] = Field(default=None, ge=0.0, description="Maximum interval in days")
    frequency_trend: FrequencyTrendLiteral = Field(
        default="INSUFFICIENT_HISTORY",
        description="Inspection frequency trend: FREQUENCY_INCREASING, FREQUENCY_STABLE, FREQUENCY_DECREASING, or INSUFFICIENT_HISTORY"
    )

    # 4. Multi-Signal Trend Classifications
    defect_trend: ProgressionTrendLiteral = Field(
        default="INSUFFICIENT_HISTORY",
        description="Progression of defect count/burden: INCREASING, STABLE, DECREASING, or INSUFFICIENT_HISTORY"
    )
    severity_trend: ProgressionTrendLiteral = Field(
        default="INSUFFICIENT_HISTORY",
        description="Progression of physical severity: INCREASING, STABLE, DECREASING, or INSUFFICIENT_HISTORY"
    )
    risk_trend: ProgressionTrendLiteral = Field(
        default="INSUFFICIENT_HISTORY",
        description="Trajectory of authoritative risk scores: INCREASING, STABLE, DECREASING, or INSUFFICIENT_HISTORY"
    )
    recurrence_pattern: RecurrencePatternLiteral = Field(
        default="INSUFFICIENT_HISTORY",
        description="Defect recurrence classification: NO_RECURRENCE, RECURRENT, PERSISTENT, or INSUFFICIENT_HISTORY"
    )
    recurrence_count: int = Field(default=0, ge=0, description="Total prior occurrences of the primary defect type")

    # 5. High-Level Deterioration Synthesis & Evidence Sufficiency
    deterioration_status: DeteriorationStatusLiteral = Field(
        default="INSUFFICIENT_HISTORY",
        description="Holistic deterioration synthesis: DETERIORATING, STABLE, IMPROVING, RECURRENT_RISK, or INSUFFICIENT_HISTORY"
    )
    evidence_sufficiency: EvidenceSufficiencyLiteral = Field(
        default="INSUFFICIENT",
        description="Historical data sufficiency: SUFFICIENT (>=3 records), LIMITED (2 records), or INSUFFICIENT (<2 records)"
    )

    # 6. Provenance & Explanations
    source_inspection_ids: List[str] = Field(default_factory=list, description="All inspection IDs included in trend analysis")
    trend_summary_explanation: str = Field(..., description="Human-auditable explanation of trend findings and methodology")
    calculation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata concerning thresholds and formulas")

    model_config = ConfigDict(extra="forbid")
