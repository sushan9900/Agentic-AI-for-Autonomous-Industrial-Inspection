"""Agent tool for querying longitudinal inspection history and memory from PostgreSQL (Phase 6A)."""

from typing import Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.database.session import SessionLocal
from backend.app.schemas.inspection_history import HistoricalInspectionContext
from backend.app.services.inspection_history import inspection_history_service
from backend.app.tools.base import BaseAgentTool


class InspectionHistoryInput(BaseModel):
    """Input parameters for get_inspection_history tool."""
    asset_id: str = Field(..., description="Target industrial asset identifier")
    component_id: Optional[str] = Field(default=None, description="Optional target component identifier")
    defect_type: Optional[str] = Field(default=None, description="Current primary defect type classification (e.g. 'crack')")
    current_inspection_id: Optional[str] = Field(default=None, description="Current inspection ID to exclude from historical records")

    model_config = ConfigDict(extra="forbid")


class GetInspectionHistoryTool(BaseAgentTool):
    """Tool for retrieving longitudinal inspection memory, recurrence intelligence, and risk trends."""

    @property
    def name(self) -> str:
        return "get_inspection_history"

    @property
    def description(self) -> str:
        return (
            "Retrieves past inspection track records, recurrence rates, previous risk scores, "
            "authoritative actions, and deterministic risk trends for the specified asset and component."
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return InspectionHistoryInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return HistoricalInspectionContext

    def execute(self, params: InspectionHistoryInput, db: Optional[Session] = None) -> HistoricalInspectionContext:
        """Executes historical memory query using provided session or a temporary session."""
        if db is not None:
            return inspection_history_service.build_historical_context(
                db=db,
                asset_id=params.asset_id,
                component_id=params.component_id,
                defect_type=params.defect_type,
                current_inspection_id=params.current_inspection_id
            )

        session = SessionLocal()
        try:
            return inspection_history_service.build_historical_context(
                db=session,
                asset_id=params.asset_id,
                component_id=params.component_id,
                defect_type=params.defect_type,
                current_inspection_id=params.current_inspection_id
            )
        finally:
            session.close()


get_inspection_history_tool = GetInspectionHistoryTool()
