from fastapi import APIRouter
from backend.app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the current operational status of the service."
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="agentic-industrial-inspection"
    )
