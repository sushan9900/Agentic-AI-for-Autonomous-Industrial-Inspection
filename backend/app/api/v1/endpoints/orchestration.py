"""FastAPI REST endpoints for Inspection Task Orchestration & Closed-Loop Review (Phase 8)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.evidence_request import EvidenceRequestPlanResponse
from backend.app.schemas.inspection_task import (
    InspectionTaskCreate,
    InspectionTaskListResponse,
    InspectionTaskResponse,
    InspectionTaskTransitionRequest,
)
from backend.app.schemas.orchestration import OrchestrationAuditResponse
from backend.app.schemas.orchestration_approval import (
    ApprovalDecisionRequest,
    ApprovalStatus,
    OrchestrationApprovalListResponse,
    OrchestrationApprovalResponse,
)
from backend.app.schemas.task_recommendation import TaskRecommendationsResponse
from backend.app.services.evidence_request_planner import (
    InspectionDecisionNotFoundError,
    evidence_request_planner,
)
from backend.app.services.inspection_orchestrator import (
    InvalidStateTransitionError,
    UnauthorizedTransitionError,
    inspection_orchestrator,
)
from backend.app.services.inspection_task import (
    AssetNotFoundError,
    TaskNotFoundError,
    inspection_task_service,
)
from backend.app.services.inspection_task_recommender import inspection_task_recommender
from backend.app.services.orchestration_approval import (
    ApprovalAlreadyProcessedError,
    ApprovalNotFoundError,
    orchestration_approval_service,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Task Management & Lifecycle Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/inspections/tasks",
    response_model=InspectionTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Inspection Task",
    tags=["Inspection Orchestration"]
)
def create_inspection_task(
    payload: InspectionTaskCreate,
    db: Session = Depends(get_db)
) -> InspectionTaskResponse:
    try:
        return inspection_task_service.create_task(db=db, payload=payload)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create task: {e}")


@router.get(
    "/inspections/tasks",
    response_model=InspectionTaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Inspection Tasks",
    tags=["Inspection Orchestration"]
)
def list_inspection_tasks(
    asset_id: Optional[str] = Query(default=None),
    component_id: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
) -> InspectionTaskListResponse:
    return inspection_task_service.list_tasks(
        db=db,
        asset_id=asset_id,
        component_id=component_id,
        state=state,
        priority=priority,
        limit=limit,
        offset=offset
    )


@router.get(
    "/inspections/tasks/{task_id}",
    response_model=InspectionTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Task Details",
    tags=["Inspection Orchestration"]
)
def get_inspection_task(
    task_id: str,
    db: Session = Depends(get_db)
) -> InspectionTaskResponse:
    try:
        return inspection_task_service.get_task(db=db, task_id=task_id)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/inspections/tasks/{task_id}/transition",
    response_model=InspectionTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Transition Task State",
    tags=["Inspection Orchestration"]
)
def transition_inspection_task(
    task_id: str,
    request: InspectionTaskTransitionRequest,
    db: Session = Depends(get_db)
) -> InspectionTaskResponse:
    try:
        return inspection_orchestrator.transition_task(db=db, task_id=task_id, request=request)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedTransitionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---------------------------------------------------------------------------
# Task Recommendation & Human Approval Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/inspections/orchestration/recommendations",
    response_model=TaskRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Orchestration Task Recommendations",
    tags=["Inspection Orchestration"]
)
def get_task_recommendations(
    asset_id: Optional[str] = Query(default=None),
    component_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
) -> TaskRecommendationsResponse:
    return inspection_task_recommender.get_recommendations_response(
        db=db,
        asset_id=asset_id,
        component_id=component_id
    )


@router.post(
    "/inspections/orchestration/{recommendation_id}/approve",
    response_model=OrchestrationApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Orchestration Recommendation",
    tags=["Inspection Orchestration"]
)
def approve_recommendation(
    recommendation_id: str,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db)
) -> OrchestrationApprovalResponse:
    try:
        return orchestration_approval_service.process_approval(
            db=db,
            recommendation_id=recommendation_id,
            request=request
        )
    except ApprovalNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApprovalAlreadyProcessedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/inspections/orchestration/{recommendation_id}/reject",
    response_model=OrchestrationApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Orchestration Recommendation",
    tags=["Inspection Orchestration"]
)
def reject_recommendation(
    recommendation_id: str,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db)
) -> OrchestrationApprovalResponse:
    try:
        # Enforce rejection status
        request.status = ApprovalStatus.REJECTED
        return orchestration_approval_service.process_approval(
            db=db,
            recommendation_id=recommendation_id,
            request=request
        )
    except ApprovalNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApprovalAlreadyProcessedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/inspections/orchestration/approvals",
    response_model=OrchestrationApprovalListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Orchestration Approvals",
    tags=["Inspection Orchestration"]
)
def list_orchestration_approvals(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
) -> OrchestrationApprovalListResponse:
    return orchestration_approval_service.list_approvals(
        db=db,
        status=status,
        limit=limit,
        offset=offset
    )


@router.get(
    "/inspections/orchestration/audit",
    response_model=OrchestrationAuditResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Orchestration Transition Audit Trail",
    tags=["Inspection Orchestration"]
)
def get_orchestration_audit(
    task_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
) -> OrchestrationAuditResponse:
    return inspection_orchestrator.get_audit_trail(
        db=db,
        task_id=task_id,
        limit=limit,
        offset=offset
    )


# ---------------------------------------------------------------------------
# Evidence Request Planning Endpoint
# ---------------------------------------------------------------------------
@router.get(
    "/inspections/{inspection_id}/evidence-requests",
    response_model=EvidenceRequestPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Evidence Request Plan for Inspection",
    tags=["Inspection Orchestration"]
)
def get_evidence_requests_for_inspection(
    inspection_id: str,
    db: Session = Depends(get_db)
) -> EvidenceRequestPlanResponse:
    try:
        return evidence_request_planner.plan_evidence_requests(db=db, inspection_id=inspection_id)
    except InspectionDecisionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
