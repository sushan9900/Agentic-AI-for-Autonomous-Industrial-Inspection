"""Service for querying historical failure incidents from PostgreSQL."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.database.models.incident import IncidentRecord


def get_relevant_incidents(
    db: Session,
    component_type: Optional[str] = None,
    defect_type: Optional[str] = None,
    limit: int = 10
) -> List[IncidentRecord]:
    """Retrieves historical failure incidents filtered by component or defect type."""
    stmt = select(IncidentRecord)
    if component_type:
        stmt = stmt.where(IncidentRecord.component_type == component_type)
    if defect_type:
        stmt = stmt.where(IncidentRecord.defect_type == defect_type)
    stmt = stmt.order_by(IncidentRecord.occurred_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())
