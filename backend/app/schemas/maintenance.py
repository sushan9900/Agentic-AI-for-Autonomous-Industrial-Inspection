"""Pydantic v2 schemas for component maintenance records."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MaintenanceRecordBase(BaseModel):
    maintenance_id: str = Field(..., description="Unique maintenance event identifier")
    component_id: str = Field(..., description="Component identifier")
    maintenance_type: str = Field(..., description="Type of maintenance (INSPECTION, REPAIR, COATING, etc.)")
    performed_at: datetime = Field(..., description="UTC timestamp of service execution")
    description: str = Field(..., description="Maintenance work description")
    findings: Optional[str] = Field(default=None, description="Observations recorded during service")
    action_taken: str = Field(..., description="Physical remediation or inspection action performed")
    technician_team: str = Field(..., description="Responsible engineering or technician team")
    downtime_hours: Optional[float] = Field(default=None, ge=0.0)
    cost: Optional[float] = Field(default=None, ge=0.0)
    source_type: str = Field(default="production", description="Data provenance (production / development_synthetic)")


class MaintenanceRecordRead(MaintenanceRecordBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")
