"""FastAPI REST API endpoints for Human-in-the-Loop inspection reviews (Phase 2D)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.review import (
    InspectionReviewRead,
    InspectionReviewSummary,
    ReviewActionRequest,
    ReviewAuditLogRead,
    ReviewCreateRequest,
    ReviewStatus,
    ReviewUpdateRequest,
)
from backend.app.services.review.review_service import (
    InvalidStateTransitionError,
    ReviewNotFoundError,
    review_service,
)

router = APIRouter()


@router.get(
    "/reviews",
    response_model=List[InspectionReviewSummary],
    status_code=status.HTTP_200_OK,
    summary="List Inspection Reviews",
    description="Retrieves a paginated list of inspection reviews with status, priority, and component filters for the inspector queue.",
    tags=["Inspector Reviews"]
)
def list_reviews(
    status_filter: Optional[ReviewStatus] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    component_id: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> List[InspectionReviewSummary]:
    return review_service.list_reviews(
        db=db,
        status=status_filter,
        priority=priority,
        component_id=component_id,
        skip=skip,
        limit=limit
    )


@router.post(
    "/reviews",
    response_model=InspectionReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Inspection Review",
    description="Initializes a persistent Human-in-the-Loop review from an AgentInspectionAssessment response in PENDING_HUMAN_REVIEW status.",
    tags=["Inspector Reviews"]
)
def create_review(
    request: ReviewCreateRequest,
    db: Session = Depends(get_db)
) -> InspectionReviewRead:
    review = review_service.create_review(db=db, request=request)
    return review


@router.get(
    "/reviews/{review_id}",
    response_model=InspectionReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Get Inspection Review Details",
    description="Retrieves the complete review record, including immutable AI snapshots, reviewer edits, and full audit trail.",
    tags=["Inspector Reviews"]
)
def get_review(
    review_id: str,
    db: Session = Depends(get_db)
) -> InspectionReviewRead:
    try:
        return review_service.get_review(db=db, review_id=review_id)
    except ReviewNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/reviews/{review_id}",
    response_model=InspectionReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Update Review Notes or Edit Draft Work Order",
    description="Allows authorized inspectors to edit draft work order fields or add notes prior to final authorization.",
    tags=["Inspector Reviews"]
)
def update_review(
    review_id: str,
    payload: ReviewUpdateRequest,
    db: Session = Depends(get_db)
) -> InspectionReviewRead:
    try:
        return review_service.update_review(db=db, review_id=review_id, payload=payload)
    except ReviewNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reviews/{review_id}/approve",
    response_model=InspectionReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Approve Draft Work Order",
    description="Explicit human inspector action approving the work order. Transitions review status to APPROVED and logs an immutable audit event.",
    tags=["Inspector Reviews"]
)
def approve_review(
    review_id: str,
    action: ReviewActionRequest,
    db: Session = Depends(get_db)
) -> InspectionReviewRead:
    try:
        return review_service.approve_review(db=db, review_id=review_id, action=action)
    except ReviewNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reviews/{review_id}/reject",
    response_model=InspectionReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Reject Draft Work Order",
    description="Explicit human inspector action rejecting the work order. Transitions review status to REJECTED and logs an immutable audit event.",
    tags=["Inspector Reviews"]
)
def reject_review(
    review_id: str,
    action: ReviewActionRequest,
    db: Session = Depends(get_db)
) -> InspectionReviewRead:
    try:
        return review_service.reject_review(db=db, review_id=review_id, action=action)
    except ReviewNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reviews/{review_id}/request-revision",
    response_model=InspectionReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Request Revision",
    description="Requests supplementary inspection or work-order revision from engineering. Transitions review status to REVISION_REQUESTED.",
    tags=["Inspector Reviews"]
)
def request_revision(
    review_id: str,
    action: ReviewActionRequest,
    db: Session = Depends(get_db)
) -> InspectionReviewRead:
    try:
        return review_service.request_revision(db=db, review_id=review_id, action=action)
    except ReviewNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/reviews/{review_id}/audit",
    response_model=List[ReviewAuditLogRead],
    status_code=status.HTTP_200_OK,
    summary="Get Review Audit Trail",
    description="Retrieves the chronological, immutable audit log of all human and automated actions on this review.",
    tags=["Inspector Reviews"]
)
def get_review_audit_trail(
    review_id: str,
    db: Session = Depends(get_db)
) -> List[ReviewAuditLogRead]:
    try:
        return review_service.get_audit_trail(db=db, review_id=review_id)
    except ReviewNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
