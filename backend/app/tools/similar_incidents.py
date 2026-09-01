"""Agent tool for retrieving historical failure and incident records from PostgreSQL (Phase 3B)."""

from typing import List, Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from backend.app.database.models.incident import IncidentRecord
from backend.app.database.session import SessionLocal
from backend.app.tools.base import BaseAgentTool


class SimilarIncidentSummary(BaseModel):
    """Structured similar failure incident record."""
    incident_id: str
    component_type: str
    defect_type: str
    severity: str
    description: str
    root_cause: str
    corrective_action: str
    similarity_basis: str

    model_config = ConfigDict(from_attributes=True)


class SimilarIncidentsInput(BaseModel):
    """Input parameters for check_similar_incidents tool."""
    defect_type: Optional[str] = Field(default=None, description="Defect type (e.g. 'crack', 'corrosion')")
    component_type: Optional[str] = Field(default=None, description="Component type (e.g. 'PIPE_SEGMENT', 'WELD_SEAM')")
    limit: int = Field(default=5, ge=1, le=20, description="Max similar incidents to retrieve")

    model_config = ConfigDict(extra="forbid")


class SimilarIncidentsOutput(BaseModel):
    """Structured output for check_similar_incidents tool."""
    incidents_count: int
    incidents: List[SimilarIncidentSummary] = Field(default_factory=list)
    has_matches: bool = False

    model_config = ConfigDict(extra="forbid")


class CheckSimilarIncidentsTool(BaseAgentTool):
    """Tool for querying historical failure incidents from PostgreSQL."""

    @property
    def name(self) -> str:
        return "check_similar_incidents"

    @property
    def description(self) -> str:
        return (
            "Retrieves past industrial failure incidents, root causes, corrective actions, "
            "and historical failure modes matching the given defect type or component classification."
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return SimilarIncidentsInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return SimilarIncidentsOutput

    def execute(
        self,
        params: SimilarIncidentsInput,
        db: Optional[Session] = None
    ) -> SimilarIncidentsOutput:
        """Executes similar incident query in PostgreSQL."""
        session_created = False
        if db is None:
            db = SessionLocal()
            session_created = True

        try:
            query = db.query(IncidentRecord)

            conditions = []
            if params.defect_type and params.component_type:
                # Primary match: defect_type AND component_type
                exact_matches = query.filter(
                    IncidentRecord.defect_type == params.defect_type.lower(),
                    IncidentRecord.component_type == params.component_type.upper()
                ).limit(params.limit).all()

                if exact_matches:
                    summaries = [
                        SimilarIncidentSummary(
                            incident_id=r.incident_id,
                            component_type=r.component_type,
                            defect_type=r.defect_type,
                            severity=r.severity,
                            description=r.description,
                            root_cause=r.root_cause,
                            corrective_action=r.corrective_action,
                            similarity_basis=f"Exact match on defect_type '{params.defect_type}' and component_type '{params.component_type}'"
                        )
                        for r in exact_matches
                    ]
                    return SimilarIncidentsOutput(
                        incidents_count=len(summaries),
                        incidents=summaries,
                        has_matches=True
                    )

            # Secondary fallback: match on defect_type OR component_type
            if params.defect_type:
                query_by_defect = db.query(IncidentRecord).filter(
                    IncidentRecord.defect_type == params.defect_type.lower()
                ).limit(params.limit).all()
                if query_by_defect:
                    summaries = [
                        SimilarIncidentSummary(
                            incident_id=r.incident_id,
                            component_type=r.component_type,
                            defect_type=r.defect_type,
                            severity=r.severity,
                            description=r.description,
                            root_cause=r.root_cause,
                            corrective_action=r.corrective_action,
                            similarity_basis=f"Matched defect_type '{params.defect_type}' across components"
                        )
                        for r in query_by_defect
                    ]
                    return SimilarIncidentsOutput(
                        incidents_count=len(summaries),
                        incidents=summaries,
                        has_matches=True
                    )

            if params.component_type:
                query_by_comp = db.query(IncidentRecord).filter(
                    IncidentRecord.component_type == params.component_type.upper()
                ).limit(params.limit).all()
                if query_by_comp:
                    summaries = [
                        SimilarIncidentSummary(
                            incident_id=r.incident_id,
                            component_type=r.component_type,
                            defect_type=r.defect_type,
                            severity=r.severity,
                            description=r.description,
                            root_cause=r.root_cause,
                            corrective_action=r.corrective_action,
                            similarity_basis=f"Matched component_type '{params.component_type}' across failure modes"
                        )
                        for r in query_by_comp
                    ]
                    return SimilarIncidentsOutput(
                        incidents_count=len(summaries),
                        incidents=summaries,
                        has_matches=True
                    )

            return SimilarIncidentsOutput(incidents_count=0, incidents=[], has_matches=False)
        finally:
            if session_created:
                db.close()


# Global tool instance
check_similar_incidents_tool = CheckSimilarIncidentsTool()
