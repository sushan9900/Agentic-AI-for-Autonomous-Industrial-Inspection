"""Pydantic v2 schemas for industrial components."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ComponentBase(BaseModel):
    component_id: str = Field(..., description="Unique physical component identifier")
    asset_id: str = Field(..., description="Parent asset identifier")
    component_type: str = Field(..., description="Component type (e.g. PIPE_SEGMENT, WELD_SEAM, FLANGE)")
    name: str = Field(..., description="Component designation")
    material: Optional[str] = None
    location_description: Optional[str] = None
    installation_date: Optional[date] = None
    status: str = Field(default="NORMAL", description="Component inspection health status")
    source_type: str = Field(default="production", description="Data provenance (production / development_synthetic)")


class ComponentRead(ComponentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")
