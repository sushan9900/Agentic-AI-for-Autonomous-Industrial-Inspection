"""FastAPI endpoints for component intelligence and historical context (Phase 2B)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.context import HistoricalContext
from backend.app.services.context.context_service import context_service

router = APIRouter()


@router.get(
    "/components/{component_id}/context",
    response_model=HistoricalContext,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Component Historical Context and Asset Intelligence",
    description="Fetches full relational asset metadata, maintenance logs, prior inspections, work orders, and related failure incidents from PostgreSQL.",
    tags=["Asset Intelligence"]
)
def get_component_historical_context(
    component_id: str,
    db: Session = Depends(get_db)
) -> HistoricalContext:
    """Retrieves authoritative historical context for an inspectable industrial component."""
    try:
        context = context_service.get_component_context(db=db, component_id=component_id)
        if context is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industrial component with ID '{component_id}' was not found in the asset database."
            )
        return context
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query database for component context: {str(e)}"
        )
