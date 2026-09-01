"""Abstract base interface for LLM inference providers."""

from abc import ABC, abstractmethod
from backend.app.llm.schemas import LLMGenerationRequest, LLMGenerationResponse, LLMHealthStatus


class BaseLLMProvider(ABC):
    """Abstract interface for local and decoupled LLM execution providers."""

    @abstractmethod
    def health_check(self) -> LLMHealthStatus:
        """Verifies if the LLM provider service is active, reachable, and ready."""
        pass

    @abstractmethod
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        """Executes text/structured generation against the underlying model."""
        pass

    @abstractmethod
    def model_name(self) -> str:
        """Returns the active model identifier."""
        pass
