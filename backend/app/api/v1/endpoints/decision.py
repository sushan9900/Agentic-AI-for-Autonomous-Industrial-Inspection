"""FastAPI endpoint for inspection decision evaluation (Phase 2A)."""

from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.decision import InspectionDecision
from backend.app.services.decision.decision_service import decision_service
from vision.schemas.evidence import VisionEvidence

router = APIRouter()


@router.post(
    "/inspection/decision",
    response_model=InspectionDecision,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Vision Evidence and Generate Inspection Decision",
    description="Consumes a validated VisionEvidence v1.0 payload and applies deterministic engineering rules to produce an auditable InspectionDecision.",
    tags=["Decision Engine"]
)
async def create_inspection_decision(evidence: VisionEvidence) -> InspectionDecision:
    """Evaluates vision evidence through the deterministic decision engine."""
    try:
        decision = decision_service.evaluate_inspection(evidence)
        return decision
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Evidence validation failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal decision evaluation error: {str(e)}"
        )
