"""Validation and explicit failure mode handlers for the Agentic Decision Engine (Phase 3B)."""

import json
from typing import Any, Dict, Optional, Tuple
from pydantic import ValidationError
from vision.schemas.evidence import VisionEvidence


# Explicit Failure Mode Exceptions
class AgentFailureError(Exception):
    """Base exception for agent execution failures."""
    def __init__(self, message: str, failure_code: str):
        super().__init__(message)
        self.failure_code = failure_code


class VisionEvidenceInvalidError(AgentFailureError):
    def __init__(self, message: str = "Vision evidence is invalid or does not match VisionEvidence v1.0 contract."):
        super().__init__(message, "VISION_EVIDENCE_INVALID")


class AssetNotFoundError(AgentFailureError):
    def __init__(self, message: str = "Target asset not found in asset database."):
        super().__init__(message, "ASSET_NOT_FOUND")


class MaintenanceHistoryUnavailableError(AgentFailureError):
    def __init__(self, message: str = "Maintenance history could not be queried."):
        super().__init__(message, "MAINTENANCE_HISTORY_UNAVAILABLE")


class ThresholdNotFoundError(AgentFailureError):
    def __init__(self, message: str = "Severity thresholds could not be determined."):
        super().__init__(message, "THRESHOLD_NOT_FOUND")


class SimilarIncidentsUnavailableError(AgentFailureError):
    def __init__(self, message: str = "Similar incident database is unavailable."):
        super().__init__(message, "SIMILAR_INCIDENTS_UNAVAILABLE")


class LLMUnavailableError(AgentFailureError):
    def __init__(self, message: str = "Local Ollama LLM service is offline or unreachable."):
        super().__init__(message, "LLM_UNAVAILABLE")


class LLMInvalidOutputError(AgentFailureError):
    def __init__(self, message: str = "LLM output could not be parsed into valid structured schema."):
        super().__init__(message, "LLM_INVALID_OUTPUT")


class InsufficientEvidenceError(AgentFailureError):
    def __init__(self, message: str = "Insufficient evidence to formulate operational decision."):
        super().__init__(message, "INSUFFICIENT_EVIDENCE")


class DatabaseError(AgentFailureError):
    def __init__(self, message: str = "Database transaction failed."):
        super().__init__(message, "DATABASE_ERROR")


class AgentValidator:
    """Validates evidence inputs, schema boundaries, and structured LLM outputs."""

    @staticmethod
    def validate_vision_evidence(evidence_data: Any) -> VisionEvidence:
        """Validates that input data conforms to VisionEvidence v1.0."""
        if isinstance(evidence_data, VisionEvidence):
            return evidence_data

        if not isinstance(evidence_data, dict):
            raise VisionEvidenceInvalidError("Vision evidence input must be a dictionary or VisionEvidence instance.")

        try:
            return VisionEvidence.model_validate(evidence_data)
        except ValidationError as e:
            raise VisionEvidenceInvalidError(f"VisionEvidence validation failed: {str(e)}")

    @staticmethod
    def parse_and_validate_llm_json(raw_text: str) -> Dict[str, Any]:
        """
        Parses JSON from LLM text output with markdown fence stripping and 1 repair attempt.
        """
        cleaned = raw_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Controlled single repair attempt: extract first and last curly braces
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end+1])
                except json.JSONDecodeError:
                    pass

            raise LLMInvalidOutputError("LLM response did not contain valid JSON structure.")
