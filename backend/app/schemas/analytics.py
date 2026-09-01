"""Pydantic v2 schemas for defect analytics, operational risk, trends, and timelines (Phase 3A)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DefectRecordRead(BaseModel):
    """Normalized physical defect record."""
    defect_id: str
    inspection_id: str
    asset_id: str
    component_id: Optional[str] = None
    defect_type: str
    confidence: float
    affected_area_percentage: Optional[float] = None
    bounding_box_area_percentage: Optional[float] = None
    crack_length_pixels: Optional[float] = None
    crack_width_estimate_pixels: Optional[float] = None
    location_type: Optional[str] = None
    detection_timestamp: datetime
    raw_evidence_detection_id: Optional[str] = None
    source_type: str

    model_config = ConfigDict(from_attributes=True)


class DefectTrendPoint(BaseModel):
    """Single time-series point in defect trend history."""
    timestamp: datetime
    inspection_id: str
    defect_count: int
    max_affected_area_percentage: float
    total_crack_length_pixels: float
    avg_confidence: float
    priority: str

    model_config = ConfigDict(from_attributes=True)


class DefectTrendAnalysis(BaseModel):
    """Deterministic trend metrics across an asset's inspection history."""
    asset_id: str
    total_inspections: int
    total_defects_detected: int
    average_defects_per_inspection: float
    defect_count_trend: str  # "INCREASING", "DECREASING", "STABLE", "INSUFFICIENT_DATA"
    area_severity_trend: str  # "EXPANDING", "STABLE", "RESOLVED"
    average_confidence: float
    average_days_between_inspections: Optional[float] = None
    recurring_defect_types: List[str] = Field(default_factory=list)
    time_series: List[DefectTrendPoint] = Field(default_factory=list)


class AssetRiskSnapshot(BaseModel):
    """Deterministic and explainable operational risk indicator for an industrial asset."""
    asset_id: str
    risk_score: int = Field(..., ge=0, le=100, description="Deterministic risk indicator (0-100)")
    risk_band: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    contributing_factors: List[str] = Field(default_factory=list, description="Explicit explainability breakdown")
    evidence_inspection_ids: List[str] = Field(default_factory=list)
    unresolved_work_orders_count: int = 0
    recurring_defects_count: int = 0
    days_since_last_inspection: Optional[int] = None
    calculation_timestamp: datetime
    disclaimer: str = "AI-assisted operational risk indicator — human engineering review required."


class TimelineEvent(BaseModel):
    """Single chronological event in the unified asset lifecycle."""
    event_id: str
    asset_id: str
    component_id: Optional[str] = None
    event_type: str  # "INSPECTION", "DEFECT_DETECTED", "ASSESSMENT_GENERATED", "WORK_ORDER_CREATED", "WORK_ORDER_APPROVED", "WORK_ORDER_REJECTED", "REVISION_REQUESTED", "MAINTENANCE_PERFORMED", "INCIDENT"
    timestamp: datetime
    title: str
    description: str
    source_reference: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetTimelineResponse(BaseModel):
    """Unified chronological lifecycle timeline for an asset."""
    asset_id: str
    events_count: int
    events: List[TimelineEvent] = Field(default_factory=list)


class AnalyticsOverviewResponse(BaseModel):
    """High-level platform inspection and risk metrics."""
    total_assets: int
    total_inspections: int
    total_detected_defects: int
    open_reviews_count: int
    approved_work_orders_count: int
    high_risk_assets_count: int
    critical_risk_assets_count: int
    recent_inspections: List[Dict[str, Any]] = Field(default_factory=list)


class DefectAnalyticsResponse(BaseModel):
    """Breakdown of defects across types, severities, and assets."""
    total_defects: int
    defects_by_type: Dict[str, int]
    avg_confidence_by_type: Dict[str, float]
    top_affected_assets: List[Dict[str, Any]]


class RiskAnalyticsResponse(BaseModel):
    """Risk band distribution and high-risk priority queue."""
    risk_band_distribution: Dict[str, int]
    high_risk_assets: List[Dict[str, Any]]
    average_fleet_risk_score: float
