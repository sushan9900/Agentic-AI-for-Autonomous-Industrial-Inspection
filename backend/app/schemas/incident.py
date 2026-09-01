"""Pydantic v2 schemas for historical failure incidents."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class IncidentRecordBase(BaseModel):
    incident_id: str = Field(..., description="Unique incident report identifier")
    component_type: str = Field(..., description="Affected component category")
    defect_type: str = Field(..., description="Identified defect type")
    description: str = Field(..., description="Incident narrative")
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    severity: str = Field(..., description="Incident severity level")
    occurred_at: datetime
    resolved_at: Optional[datetime] = None
    source_type: str = Field(default="production", description="Data provenance (production / development_synthetic)")


class IncidentRecordRead(IncidentRecordBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")
