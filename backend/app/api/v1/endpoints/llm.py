"""FastAPI endpoint for checking local LLM provider health (Phase 2C)."""

from fastapi import APIRouter, status
from backend.app.llm.schemas import LLMHealthStatus
from backend.app.llm.service import llm_service

router = APIRouter()


@router.get(
    "/llm/health",
    response_model=LLMHealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Check Local LLM Provider Health",
    description="Probes local Ollama instance and verifies availability of the configured model.",
    tags=["LLM Inference"]
)
def get_llm_health() -> LLMHealthStatus:
    """Queries local Ollama health check."""
    provider = llm_service.get_provider()
    return provider.health_check()
