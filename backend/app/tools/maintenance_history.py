"""Agent tool for querying structured maintenance history from PostgreSQL (Phase 2B/3B)."""

from datetime import datetime
from typing import List, Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session
from backend.app.database.models.component import Component
from backend.app.database.models.maintenance import MaintenanceRecord
from backend.app.database.session import SessionLocal
from backend.app.tools.base import BaseAgentTool


class MaintenanceRecordSummary(BaseModel):
    """Normalized structured maintenance record."""
    maintenance_id: str
    component_id: str
    maintenance_type: str
    performed_at: datetime
    description: str
    findings: Optional[str] = None
    action_taken: str
    downtime_hours: float
    cost: Optional[float] = None
    technician_team: str

    model_config = ConfigDict(from_attributes=True)


class MaintenanceHistoryInput(BaseModel):
    """Input parameters for get_maintenance_history tool."""
    asset_id: Optional[str] = Field(default=None, description="Asset identifier (e.g. 'ASSET-PL-01')")
    component_id: Optional[str] = Field(default=None, description="Component identifier (e.g. 'PIPE-SEG-4021')")
    limit: int = Field(default=10, ge=1, le=50, description="Max historical records to retrieve")

    model_config = ConfigDict(extra="forbid")


class MaintenanceHistoryOutput(BaseModel):
    """Structured output for get_maintenance_history tool."""
    component_id: Optional[str] = None
    asset_id: Optional[str] = None
    found: bool = False
    maintenance_count: int = 0
    records_count: int = 0
    has_history: bool = False
    latest_service_date: Optional[datetime] = None
    records: List[MaintenanceRecordSummary] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class GetMaintenanceHistoryTool(BaseAgentTool):
    """Tool for querying maintenance records from PostgreSQL."""

    @property
    def name(self) -> str:
        return "get_maintenance_history"

    @property
    def description(self) -> str:
        return (
            "Queries PostgreSQL for past maintenance records, performed repairs, work findings, "
            "recorded downtime hours, costs, and technician team notes."
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return MaintenanceHistoryInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return MaintenanceHistoryOutput

    def execute(
        self,
        params: MaintenanceHistoryInput,
        db: Optional[Session] = None
    ) -> MaintenanceHistoryOutput:
        """Executes maintenance history retrieval."""
        session_created = False
        if db is None:
            db = SessionLocal()
            session_created = True

        try:
            query = db.query(MaintenanceRecord)

            if params.component_id:
                query = query.filter(MaintenanceRecord.component_id == params.component_id)
            elif params.asset_id:
                comp_ids = db.query(Component.component_id).filter(Component.asset_id == params.asset_id).all()
                c_ids = [c[0] for c in comp_ids]
                if not c_ids:
                    return MaintenanceHistoryOutput(
                        component_id=params.component_id,
                        asset_id=params.asset_id,
                        found=False,
                        maintenance_count=0,
                        records_count=0,
                        records=[],
                        has_history=False,
                        latest_service_date=None
                    )
                query = query.filter(MaintenanceRecord.component_id.in_(c_ids))
            else:
                return MaintenanceHistoryOutput(
                    component_id=params.component_id,
                    asset_id=params.asset_id,
                    found=False,
                    maintenance_count=0,
                    records_count=0,
                    records=[],
                    has_history=False,
                    latest_service_date=None
                )

            records = (
                query.order_by(desc(MaintenanceRecord.performed_at))
                .limit(params.limit)
                .all()
            )

            summaries = [
                MaintenanceRecordSummary(
                    maintenance_id=r.maintenance_id,
                    component_id=r.component_id,
                    maintenance_type=r.maintenance_type,
                    performed_at=r.performed_at,
                    description=r.description,
                    findings=r.findings,
                    action_taken=r.action_taken,
                    downtime_hours=r.downtime_hours,
                    cost=r.cost,
                    technician_team=r.technician_team
                )
                for r in records
            ]

            count = len(summaries)
            latest_date = summaries[0].performed_at if summaries else None

            return MaintenanceHistoryOutput(
                component_id=params.component_id,
                asset_id=params.asset_id,
                found=count > 0,
                maintenance_count=count,
                records_count=count,
                has_history=count > 0,
                latest_service_date=latest_date,
                records=summaries
            )
        finally:
            if session_created:
                db.close()


# Global tool instance
get_maintenance_history_tool = GetMaintenanceHistoryTool()
