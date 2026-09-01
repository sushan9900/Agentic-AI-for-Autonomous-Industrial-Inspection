"""Pydantic v2 schemas for historical inspection records."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class InspectionRecordBase(BaseModel):
    inspection_id: str = Field(..., description="Unique inspection transaction identifier")
    component_id: str = Field(..., description="Target component identifier")
    inspection_timestamp: datetime = Field(..., description="UTC timestamp of inspection")
    inspection_method: str = Field(..., description="Inspection methodology (AUTONOMOUS_VISION, MANUAL_VISUAL, etc.)")
    defect_type: str = Field(..., description="Classified defect type (crack, corrosion, none)")
    severity: str = Field(..., description="Recorded severity or priority rating")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    findings: str = Field(..., description="Summary of inspection findings")
    evidence_reference: Optional[str] = Field(default=None, description="Hash or file path to evidence artifact")
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    source_type: str = Field(default="production", description="Data provenance (production / development_synthetic)")


class InspectionRecordRead(InspectionRecordBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")
