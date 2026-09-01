"""Base tool interface for future agentic tools (Phase 2A Foundation)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel


class BaseAgentTool(ABC):
    """Abstract base class for structured tools executable by autonomous agent workflows."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical tool identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of tool capabilities and parameter requirements."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Type[BaseModel]:
        """Pydantic schema defining validated tool input parameters."""
        pass

    @property
    @abstractmethod
    def output_schema(self) -> Type[BaseModel]:
        """Pydantic schema defining structured tool output."""
        pass

    @abstractmethod
    def execute(self, params: BaseModel) -> BaseModel:
        """Executes tool logic and returns structured output."""
        pass
