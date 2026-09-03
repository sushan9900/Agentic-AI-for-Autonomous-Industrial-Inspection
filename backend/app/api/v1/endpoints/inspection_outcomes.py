"""FastAPI REST endpoints for Inspection Review Outcomes & Adaptive Learning (Phase 7)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.adaptive_recommendation import AdaptiveRecommendationsResponse
from backend.app.schemas.inspection_outcome import (
    InspectionOutcomeCreate,
    InspectionOutcomeListResponse,
    InspectionOutcomeResponse,
)
from backend.app.schemas.learning_metrics import (
    LearningMetricsSummary,
    LearningPatternsResponse,
)
from backend.app.services.adaptive_recommendation import adaptive_recommendation_service
from backend.app.services.inspection_learning import inspection_learning_service
from backend.app.services.inspection_outcome import (
    DuplicateOutcomeError,
    InspectionNotFoundError,
    OutcomeNotFoundError,
    inspection_outcome_service,
)

router = APIRouter()


@router.post(
    "/inspections/{inspection_id}/outcome",
    response_model=InspectionOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Human Review Outcome",
    description="Captures and finalizes an authorized human inspector review outcome, snapshotting AI predictions.",
    tags=["Inspection Learning & Outcomes"]
)
def record_inspection_outcome(
    inspection_id: str,
    payload: InspectionOutcomeCreate,
    db: Session = Depends(get_db)
) -> InspectionOutcomeResponse:
    try:
        return inspection_outcome_service.record_outcome(
            db=db,
            inspection_id=inspection_id,
            payload=payload
        )
    except InspectionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateOutcomeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to record outcome: {e}")


@router.get(
    "/inspections/outcomes",
    response_model=InspectionOutcomeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Human Review Outcomes",
    description="Retrieves a paginated list of finalized inspection review outcomes.",
    tags=["Inspection Learning & Outcomes"]
)
def list_inspection_outcomes(
    asset_id: Optional[str] = Query(default=None, description="Filter by asset ID"),
    component_id: Optional[str] = Query(default=None, description="Filter by component ID"),
    review_status: Optional[str] = Query(default=None, description="Filter by outcome status: APPROVED, CORRECTED, REJECTED"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
) -> InspectionOutcomeListResponse:
    return inspection_outcome_service.list_outcomes(
        db=db,
        asset_id=asset_id,
        component_id=component_id,
        review_status=review_status,
        limit=limit,
        offset=offset
    )


@router.get(
    "/inspections/outcomes/{inspection_id}",
    response_model=InspectionOutcomeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Specific Inspection Outcome",
    description="Retrieves the recorded review outcome and AI prediction comparison for a specific inspection ID.",
    tags=["Inspection Learning & Outcomes"]
)
def get_inspection_outcome(
    inspection_id: str,
    db: Session = Depends(get_db)
) -> InspectionOutcomeResponse:
    try:
        return inspection_outcome_service.get_outcome(db=db, inspection_id=inspection_id)
    except OutcomeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/inspections/learning/metrics",
    response_model=LearningMetricsSummary,
    status_code=status.HTTP_200_OK,
    summary="Get Learning Agreement Metrics",
    description="Calculates deterministic agreement, false-positive, false-negative, and correction metrics.",
    tags=["Inspection Learning & Outcomes"]
)
def get_learning_metrics(
    asset_id: Optional[str] = Query(default=None, description="Scope metrics to specific asset"),
    component_id: Optional[str] = Query(default=None, description="Scope metrics to specific component"),
    db: Session = Depends(get_db)
) -> LearningMetricsSummary:
    return inspection_learning_service.calculate_metrics(
        db=db,
        asset_id=asset_id,
        component_id=component_id
    )


@router.get(
    "/inspections/learning/patterns",
    response_model=LearningPatternsResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect Error Patterns",
    description="Identifies deterministic recurring discrepancy patterns across historical review outcomes.",
    tags=["Inspection Learning & Outcomes"]
)
def get_error_patterns(
    asset_id: Optional[str] = Query(default=None, description="Scope error patterns to asset"),
    component_id: Optional[str] = Query(default=None, description="Scope error patterns to component"),
    db: Session = Depends(get_db)
) -> LearningPatternsResponse:
    patterns = inspection_learning_service.detect_error_patterns(
        db=db,
        asset_id=asset_id,
        component_id=component_id
    )
    return LearningPatternsResponse(
        total_patterns=len(patterns),
        patterns=patterns
    )


@router.get(
    "/inspections/learning/recommendations",
    response_model=AdaptiveRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Adaptive Recommendations",
    description="Generates explainable, deterministic advisory recommendations based on active error patterns.",
    tags=["Inspection Learning & Outcomes"]
)
def get_adaptive_recommendations(
    asset_id: Optional[str] = Query(default=None, description="Scope recommendations to asset"),
    component_id: Optional[str] = Query(default=None, description="Scope recommendations to component"),
    db: Session = Depends(get_db)
) -> AdaptiveRecommendationsResponse:
    return adaptive_recommendation_service.get_recommendations_response(
        db=db,
        asset_id=asset_id,
        component_id=component_id
    )
