"""Service for querying previous inspection records from PostgreSQL."""

from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.database.models.inspection import InspectionRecord
from backend.app.database.models.work_order import WorkOrder


def get_component_inspection_history(
    db: Session,
    component_id: str
) -> List[InspectionRecord]:
    """Retrieves all historical inspection records for a component ordered by inspection_timestamp descending."""
    stmt = (
        select(InspectionRecord)
        .where(InspectionRecord.component_id == component_id)
        .order_by(InspectionRecord.inspection_timestamp.desc())
    )
    return list(db.scalars(stmt).all())


def get_component_work_orders(
    db: Session,
    component_id: str
) -> List[WorkOrder]:
    """Retrieves all historical work orders for a component ordered by created_at descending."""
    stmt = (
        select(WorkOrder)
        .where(WorkOrder.component_id == component_id)
        .order_by(WorkOrder.created_at.desc())
    )
    return list(db.scalars(stmt).all())
