from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    agent,
    analytics,
    assessment,
    assets,
    components,
    decision,
    health,
    images,
    inspection_outcomes,
    llm,
    reviews,
    system,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(system.router, tags=["System Status"])
api_router.include_router(agent.router, tags=["Agentic Decision Engine"])
api_router.include_router(decision.router, tags=["Decision Engine"])
api_router.include_router(components.router, tags=["Asset Intelligence"])
api_router.include_router(llm.router, tags=["LLM Inference"])
api_router.include_router(assessment.router, tags=["Agentic Assessment"])
api_router.include_router(reviews.router, tags=["Inspector Reviews"])
api_router.include_router(inspection_outcomes.router, tags=["Inspection Learning & Outcomes"])
api_router.include_router(images.router, tags=["Inspection Images"])
api_router.include_router(assets.router, tags=["Asset Management"])
api_router.include_router(analytics.router, tags=["Fleet Analytics"])
