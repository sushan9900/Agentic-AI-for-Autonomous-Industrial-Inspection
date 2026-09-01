"""Pydantic v2 domain schemas for industrial assets."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.component import ComponentRead


class AssetBase(BaseModel):
    """Base fields shared across asset creation and reads."""
    asset_id: str = Field(..., description="Unique industrial asset identifier (e.g. PIPE-001)")
    asset_code: Optional[str] = Field(default=None, description="Optional engineering plant code")
    asset_type: str = Field(..., description="Classification category (e.g. PIPELINE, STORAGE_TANK)")
    name: str = Field(..., description="Descriptive asset name")
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    installation_date: Optional[date] = None
    location: str = Field(..., description="Physical plant zone or facility location")
    operational_status: str = Field(default="OPERATIONAL", description="Current operational state")
    warranty_start: Optional[date] = None
    warranty_end: Optional[date] = None
    source_type: str = Field(default="production", description="Data provenance classification")

    model_config = ConfigDict(from_attributes=True)


class AssetCreate(AssetBase):
    """Request payload for creating a new asset."""
    pass


class AssetUpdate(BaseModel):
    """Request payload for updating asset properties."""
    asset_code: Optional[str] = None
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    operational_status: Optional[str] = None
    warranty_end: Optional[date] = None

    model_config = ConfigDict(extra="forbid")


class AssetRead(AssetBase):
    """Standard API representation of an industrial asset."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetSummaryRead(BaseModel):
    """Concise representation for asset directory and dashboard tables."""
    asset_id: str
    asset_code: Optional[str] = None
    name: str
    asset_type: str
    location: str
    operational_status: str
    last_inspection_date: Optional[datetime] = None
    total_defects_count: int = 0
    open_work_orders_count: int = 0
    current_risk_score: int = 0
    current_risk_band: str = "LOW"

    model_config = ConfigDict(from_attributes=True)


class AssetDetailRead(AssetRead):
    """Detailed asset view with nested components and summary analytics."""
    components: List[ComponentRead] = Field(default_factory=list)
    total_defects_count: int = 0
    total_inspections_count: int = 0
    open_work_orders_count: int = 0
    current_risk_score: int = 0
    current_risk_band: str = "LOW"

    model_config = ConfigDict(from_attributes=True)
