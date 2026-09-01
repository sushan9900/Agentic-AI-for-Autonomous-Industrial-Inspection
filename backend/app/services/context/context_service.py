"""Central context aggregation service retrieving comprehensive component intelligence from PostgreSQL."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models.component import Component
from backend.app.schemas.asset import AssetRead
from backend.app.schemas.component import ComponentRead
from backend.app.schemas.context import HistoricalContext
from backend.app.schemas.incident import IncidentRecordRead
from backend.app.schemas.inspection_record import InspectionRecordRead
from backend.app.schemas.maintenance import MaintenanceRecordRead
from backend.app.schemas.work_order import WorkOrderRead
from backend.app.services.context.incident_service import get_relevant_incidents
from backend.app.services.context.inspection_history_service import (
    get_component_inspection_history,
    get_component_work_orders,
)
from backend.app.services.context.maintenance_service import get_component_maintenance_history


class ComponentContextService:
    """Orchestrates asset intelligence and historical maintenance record retrieval."""

    @staticmethod
    def get_component_context(
        db: Session,
        component_id: str
    ) -> Optional[HistoricalContext]:
        """
        Retrieves complete relational history for a component from PostgreSQL.
        Returns None if component does not exist.
        """
        # Query component with parent asset
        stmt = (
            select(Component)
            .options(joinedload(Component.asset))
            .where(Component.component_id == component_id)
        )
        component = db.scalar(stmt)
        if not component:
            return None

        # Query related tables
        maintenance_records = get_component_maintenance_history(db, component_id)
        inspection_records = get_component_inspection_history(db, component_id)
        work_orders = get_component_work_orders(db, component_id)
        incidents = get_relevant_incidents(db, component_type=component.component_type, limit=5)

        # Check if dataset contains synthetic development tags
        is_synthetic = (
            component.source_type == "development_synthetic"
            or component.asset.source_type == "development_synthetic"
            or any(m.source_type == "development_synthetic" for m in maintenance_records)
        )

        source_refs = {
            "database_provider": "PostgreSQL",
            "asset_table": "assets",
            "component_table": "components",
            "maintenance_count": len(maintenance_records),
            "inspection_count": len(inspection_records),
            "work_order_count": len(work_orders),
            "incident_count": len(incidents),
            "provenance_state": "SYNTHETIC_DEVELOPMENT" if is_synthetic else "PRODUCTION_VERIFIED"
        }

        return HistoricalContext(
            schema_version="1.0",
            component=ComponentRead.model_validate(component),
            asset=AssetRead.model_validate(component.asset),
            maintenance_history=[MaintenanceRecordRead.model_validate(m) for m in maintenance_records],
            previous_inspections=[InspectionRecordRead.model_validate(i) for i in inspection_records],
            previous_work_orders=[WorkOrderRead.model_validate(w) for w in work_orders],
            relevant_incidents=[IncidentRecordRead.model_validate(inc) for inc in incidents],
            source_references=source_refs,
            is_synthetic_data=is_synthetic
        )


# Global singleton instance
context_service = ComponentContextService()
