"""Service for querying component maintenance records from PostgreSQL."""

from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.database.models.maintenance import MaintenanceRecord


def get_component_maintenance_history(
    db: Session,
    component_id: str
) -> List[MaintenanceRecord]:
    """Retrieves all maintenance records for a component ordered by performed_at descending."""
    stmt = (
        select(MaintenanceRecord)
        .where(MaintenanceRecord.component_id == component_id)
        .order_by(MaintenanceRecord.performed_at.desc())
    )
    return list(db.scalars(stmt).all())
