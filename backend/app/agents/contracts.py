"""Abstract decision engine interface for provider-independent decision systems."""

from abc import ABC, abstractmethod
from typing import Optional
from backend.app.schemas.decision import InspectionDecision
from vision.schemas.evidence import VisionEvidence


class BaseDecisionEngine(ABC):
    """Abstract interface for inspection decision engines."""

    @abstractmethod
    def evaluate(
        self,
        evidence: VisionEvidence,
        decision_id: Optional[str] = None
    ) -> InspectionDecision:
        """Evaluates vision evidence and produces an authoritative InspectionDecision."""
        pass
