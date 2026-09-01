"""Agent tool for querying comprehensive component intelligence from PostgreSQL (Phase 2B)."""

from typing import Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from backend.app.database.session import SessionLocal
from backend.app.schemas.context import HistoricalContext
from backend.app.services.context.context_service import context_service
from backend.app.tools.base import BaseAgentTool


class ComponentContextInput(BaseModel):
    """Input parameters for get_component_context tool."""
    component_id: str = Field(..., description="Target industrial component identifier (e.g. 'PIPE-SEG-4021')")

    model_config = ConfigDict(extra="forbid")


class ComponentContextOutput(BaseModel):
    """Structured output for get_component_context tool."""
    component_id: str
    found: bool
    context: Optional[HistoricalContext] = None

    model_config = ConfigDict(extra="forbid")


class GetComponentContextTool(BaseAgentTool):
    """Concrete agent tool for retrieving complete asset intelligence and component context."""

    @property
    def name(self) -> str:
        return "get_component_context"

    @property
    def description(self) -> str:
        return (
            "Queries PostgreSQL for comprehensive asset intelligence, parent asset specifications, "
            "maintenance history, previous inspection records, past work orders, and related failure incidents."
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ComponentContextInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ComponentContextOutput

    def execute(
        self,
        params: ComponentContextInput,
        db: Optional[Session] = None
    ) -> ComponentContextOutput:
        """Executes the complete component context database retrieval."""
        session_created = False
        if db is None:
            db = SessionLocal()
            session_created = True

        try:
            ctx = context_service.get_component_context(db, params.component_id)
            if ctx is None:
                return ComponentContextOutput(
                    component_id=params.component_id,
                    found=False,
                    context=None
                )
            return ComponentContextOutput(
                component_id=params.component_id,
                found=True,
                context=ctx
            )
        finally:
            if session_created:
                db.close()
