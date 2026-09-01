"""Application-level decision service orchestrating evidence evaluation (Phase 2A)."""

from typing import Any, Optional
from backend.app.schemas.decision import InspectionDecision
from vision.schemas.evidence import VisionEvidence


class DecisionService:
    """Application service for inspection decision evaluations."""

    def __init__(self, engine: Optional[Any] = None):
        self._engine = engine

    @property
    def engine(self) -> Any:
        if self._engine is None:
            from backend.app.agents.decision_engine import DeterministicDecisionEngine
            self._engine = DeterministicDecisionEngine()
        return self._engine

    def evaluate_inspection(
        self,
        evidence: VisionEvidence,
        decision_id: Optional[str] = None
    ) -> InspectionDecision:
        """
        Processes a VisionEvidence contract and generates an authoritative InspectionDecision.
        """
        return self.engine.evaluate(evidence=evidence, decision_id=decision_id)


# Global service instance for API dependency injection
decision_service = DecisionService()
