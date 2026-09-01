"""LLM provider service manager (Phase 2C)."""

from typing import Optional
from backend.app.core.config import settings
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.ollama import OllamaProvider


class LLMService:
    """Service layer managing local LLM provider instances."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self._provider = provider

    def get_provider(self) -> BaseLLMProvider:
        """Retrieves or lazily instantiates the configured LLM provider."""
        if self._provider is None:
            if settings.LLM_PROVIDER.lower() == "ollama":
                self._provider = OllamaProvider(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL,
                    timeout_seconds=settings.LLM_REQUEST_TIMEOUT_SECONDS
                )
            else:
                # Default strictly to Ollama
                self._provider = OllamaProvider()
        return self._provider

    def set_provider(self, provider: BaseLLMProvider) -> None:
        """Sets an explicit LLM provider (useful for test dependency injection)."""
        self._provider = provider


# Global singleton instance
llm_service = LLMService()
