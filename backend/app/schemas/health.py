from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Status of the API service")
    service: str = Field(default="agentic-industrial-inspection", description="Name of the service")
