"""Pydantic v2 schemas for maintenance work orders."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkOrderBase(BaseModel):
    work_order_id: str = Field(..., description="Unique work order identifier")
    component_id: str = Field(..., description="Target component identifier")
    inspection_id: Optional[str] = Field(default=None, description="Linked inspection identifier")
    priority: str = Field(..., description="Operational priority (LOW, MEDIUM, HIGH, CRITICAL)")
    status: str = Field(default="PENDING_APPROVAL", description="Work order workflow status")
    recommended_action: str = Field(..., description="Prescribed remediation work")
    assigned_team: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    downtime_hours: Optional[float] = None
    source_type: str = Field(default="production", description="Data provenance (production / development_synthetic)")


class WorkOrderRead(WorkOrderBase):
    id: int

    model_config = ConfigDict(from_attributes=True, extra="forbid")
