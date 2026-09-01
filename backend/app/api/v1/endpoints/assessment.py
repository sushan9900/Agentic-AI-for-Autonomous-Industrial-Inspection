"""FastAPI endpoint for multi-modal agentic inspection assessment (Phase 2C)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.agents.inspection_agent import ComponentNotFoundError, inspection_agent
from backend.app.agents.reasoning import ReasoningParserError
from backend.app.database.session import get_db
from backend.app.llm.ollama import OllamaProviderError
from backend.app.schemas.agent_assessment import (
    InspectionAssessmentRequest,
    InspectionAssessmentResponse,
)

router = APIRouter()


@router.post(
    "/inspection/assessment",
    response_model=InspectionAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Multi-Modal Agentic Inspection Assessment & Draft Work Order",
    description="Synthesizes visual perception evidence with PostgreSQL asset history and executes local Gemma3 reasoning to produce a draft work order pending human review.",
    tags=["Agentic Assessment"]
)
def create_inspection_assessment(
    request: InspectionAssessmentRequest,
    db: Session = Depends(get_db)
) -> InspectionAssessmentResponse:
    """Executes multi-modal agent reasoning on vision evidence and historical context."""
    try:
        response = inspection_agent.assess_inspection(
            vision_evidence=request.vision_evidence,
            component_id=request.component_id,
            db=db
        )
        return response
    except ComponentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except OllamaProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local LLM provider error: {str(e)}"
        )
    except ReasoningParserError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to validate LLM structured response: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during agent reasoning: {str(e)}"
        )
