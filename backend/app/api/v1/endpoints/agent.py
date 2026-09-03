"""FastAPI REST endpoints for the Agentic Inspection Decision Engine (Phase 3B/4)."""

import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from backend.app.agents.inspection_agent import (
    AssetNotFoundError,
    VisionEvidenceInvalidError,
    inspection_decision_agent,
)
from backend.app.agents.trace import TraceEvent
from backend.app.database.session import get_db
from backend.app.schemas.agent_decision import (
    AgentDecisionListResponse,
    AgentDecisionReviewRequest,
    AgentInspectRequest,
    AgentInspectionDecision,
)
from backend.app.schemas.inspection_prioritization import InspectionPriorityQueue
from backend.app.services.agent import (
    DecisionNotFoundError,
    InvalidReviewActionError,
    agent_decision_service,
)
from backend.app.services.end_to_end_inspection import e2e_inspection_service
from backend.app.services.inspection_prioritization import inspection_prioritization_service

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB max upload
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/agent/inspect",
    response_model=AgentInspectionDecision,
    status_code=status.HTTP_200_OK,
    summary="Execute Agentic Inspection Decision Workflow",
    description=(
        "Executes the 11-stage autonomous inspection decision workflow: validating VisionEvidence, "
        "querying asset context & maintenance history, evaluating deterministic engineering thresholds, "
        "calculating explainable risk, synthesizing draft work orders, and producing a complete observable trace."
    ),
    tags=["Agentic Decision Engine"]
)
def run_agent_inspection(
    request: AgentInspectRequest,
    db: Session = Depends(get_db)
) -> AgentInspectionDecision:
    try:
        decision = inspection_decision_agent.run_inspection(
            inspection_id=request.inspection_id,
            asset_id=request.asset_id,
            evidence=request.evidence,
            db=db,
            component_id=request.component_id
        )
        # Persist decision and trace to PostgreSQL
        agent_decision_service.save_decision(db=db, decision=decision)
        return decision
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except VisionEvidenceInvalidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Agent workflow error: {str(e)}")


@router.post(
    "/agent/upload-and-inspect",
    response_model=AgentInspectionDecision,
    status_code=status.HTTP_200_OK,
    summary="Upload Inspection Image and Execute End-to-End Workflow",
    description="Validates an uploaded image, executes YOLO11n-seg inference, performs 11-stage agent reasoning, and stores the decision.",
    tags=["Agentic Decision Engine"]
)
async def upload_and_inspect(
    file: UploadFile = File(...),
    asset_id: str = Form(...),
    component_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
) -> AgentInspectionDecision:
    # 1. Validate File Extension
    original_name = file.filename or "upload.jpg"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Generate Safe Unique Filename (Prevent Path Traversal)
    safe_filename = f"{uuid.uuid4().hex[:12]}_{Path(original_name).name}"
    target_path = UPLOAD_DIR / safe_filename

    # 3. Stream File with Size Enforcement
    size = 0
    try:
        with open(target_path, "wb") as buffer:
            while chunk := await file.read(64 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if target_path.exists():
                        target_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Uploaded image exceeds the 20MB file size limit."
                    )
                buffer.write(chunk)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File save error: {str(e)}")

    if size == 0:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty (0 bytes).")

    # 4. Execute End-to-End Inspection Flow
    try:
        return e2e_inspection_service.run_e2e_inspection(
            image_path=str(target_path),
            asset_id=asset_id,
            component_id=component_id,
            db=db
        )
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inspection pipeline error: {str(e)}")


@router.get(
    "/agent/decisions",
    response_model=AgentDecisionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Agent Decisions",
    description="Retrieves a paginated and filterable list of persistent autonomous inspection decisions.",
    tags=["Agentic Decision Engine"]
)
def list_agent_decisions(
    risk_level: Optional[str] = Query(default=None, description="Filter by risk: CRITICAL, HIGH, MEDIUM, LOW"),
    operational_decision: Optional[str] = Query(default=None, description="Filter by action (e.g. URGENT_ENGINEERING_REVIEW)"),
    review_status: Optional[str] = Query(default=None, description="Filter by review status: PENDING_HUMAN_REVIEW, APPROVED, REJECTED"),
    asset_id: Optional[str] = Query(default=None, description="Filter by asset ID"),
    search: Optional[str] = Query(default=None, description="Search keyword"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
) -> AgentDecisionListResponse:
    return agent_decision_service.list_decisions(
        db=db,
        risk_level=risk_level,
        operational_decision=operational_decision,
        review_status=review_status,
        asset_id=asset_id,
        search=search,
        limit=limit,
        offset=offset
    )


@router.get(
    "/agent/kpis",
    status_code=status.HTTP_200_OK,
    summary="Get Overview KPIs",
    description="Returns aggregate counts for inspections, pending reviews, critical and high-risk findings.",
    tags=["Agentic Decision Engine"]
)
def get_overview_kpis(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return agent_decision_service.get_overview_kpis(db=db)


@router.get(
    "/agent/inspections/prioritized",
    response_model=InspectionPriorityQueue,
    status_code=status.HTTP_200_OK,
    summary="Get Prioritized Human Review Queue",
    description="Returns a transparent, deterministically prioritized queue of inspections requiring human review (Phase 6D).",
    tags=["Agentic Decision Engine"]
)
def get_prioritized_inspections(
    status_filter: Optional[str] = Query(default="PENDING_HUMAN_REVIEW", alias="status", description="Filter by review status"),
    priority_class: Optional[str] = Query(default=None, description="Filter by review priority class: CRITICAL, HIGH, MEDIUM, LOW"),
    asset_id: Optional[str] = Query(default=None, description="Filter by asset ID"),
    component_id: Optional[str] = Query(default=None, description="Filter by component ID"),
    limit: int = Query(default=50, ge=1, le=100, description="Max items to return"),
    db: Session = Depends(get_db)
) -> InspectionPriorityQueue:
    return inspection_prioritization_service.get_prioritized_queue(
        db=db,
        status_filter=status_filter,
        priority_class=priority_class,
        asset_id=asset_id,
        component_id=component_id,
        limit=limit
    )


@router.get(
    "/agent/decisions/{decision_id}",
    response_model=AgentInspectionDecision,
    status_code=status.HTTP_200_OK,
    summary="Get Agent Decision",
    description="Retrieves a persisted autonomous inspection decision record from PostgreSQL.",
    tags=["Agentic Decision Engine"]
)
def get_agent_decision(
    decision_id: str,
    db: Session = Depends(get_db)
) -> AgentInspectionDecision:
    try:
        return agent_decision_service.get_decision(db=db, decision_id=decision_id)
    except DecisionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/agent/decisions/{decision_id}/trace",
    response_model=List[TraceEvent],
    status_code=status.HTTP_200_OK,
    summary="Get Agent Decision Reasoning Trace",
    description="Retrieves the complete sequential observable trace events for an agent decision.",
    tags=["Agentic Decision Engine"]
)
def get_agent_decision_trace(
    decision_id: str,
    db: Session = Depends(get_db)
) -> List[TraceEvent]:
    try:
        return agent_decision_service.get_decision_traces(db=db, decision_id=decision_id)
    except DecisionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/agent/decisions/{decision_id}/review",
    response_model=AgentInspectionDecision,
    status_code=status.HTTP_200_OK,
    summary="Submit Human Review Authorization",
    description="Applies human inspector approval, rejection, or further inspection request. Strictly records the human authorization without automated maintenance execution.",
    tags=["Agentic Decision Engine"]
)
def review_agent_decision(
    decision_id: str,
    review_req: AgentDecisionReviewRequest,
    db: Session = Depends(get_db)
) -> AgentInspectionDecision:
    try:
        return agent_decision_service.apply_review(
            db=db,
            decision_id=decision_id,
            reviewer_name=review_req.reviewer_name,
            review_action=review_req.review_action,
            review_comment=review_req.review_comment
        )
    except DecisionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidReviewActionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
