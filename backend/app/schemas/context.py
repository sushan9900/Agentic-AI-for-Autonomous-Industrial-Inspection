"""Versioned HistoricalContext contract (v1.0) aggregating asset intelligence."""

from datetime import datetime, timezone
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.asset import AssetRead
from backend.app.schemas.component import ComponentRead
from backend.app.schemas.incident import IncidentRecordRead
from backend.app.schemas.inspection_record import InspectionRecordRead
from backend.app.schemas.maintenance import MaintenanceRecordRead
from backend.app.schemas.work_order import WorkOrderRead


class HistoricalContext(BaseModel):
    """Authoritative, versioned historical context contract for industrial components."""
    schema_version: str = Field(default="1.0", description="Contract specification version")
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of context extraction"
    )
    component: ComponentRead = Field(..., description="Target component details")
    asset: AssetRead = Field(..., description="Parent asset metadata and location")
    maintenance_history: List[MaintenanceRecordRead] = Field(
        default_factory=list,
        description="Historical maintenance and servicing events"
    )
    previous_inspections: List[InspectionRecordRead] = Field(
        default_factory=list,
        description="Prior inspection findings and severity logs"
    )
    previous_work_orders: List[WorkOrderRead] = Field(
        default_factory=list,
        description="Past work orders and remediation history"
    )
    relevant_incidents: List[IncidentRecordRead] = Field(
        default_factory=list,
        description="Historical incidents related by component type or defect patterns"
    )
    source_references: Dict[str, Any] = Field(
        default_factory=dict,
        description="Data provenance references and query metadata"
    )
    is_synthetic_data: bool = Field(
        default=False,
        description="True if context was constructed from development/synthetic seed records"
    )

    model_config = ConfigDict(extra="forbid")
