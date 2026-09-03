"""Validation, fabrication guards, and explicit failure mode handlers for the Agentic Decision Engine (Phase 3B/5C)."""

import json
from typing import Any, Dict, List, Optional, Tuple
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
    """Validates evidence inputs, schema boundaries, evidence grounding, and structured LLM outputs."""

    # Protected authoritative fields that LLM is NEVER permitted to set or override
    FORBIDDEN_AUTHORITATIVE_LLM_FIELDS = {
        "risk_score",
        "risk_level",
        "operational_decision",
        "priority",
        "human_review_required",
        "review_status",
        "status",
        "is_approved"
    }

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
        Parses JSON from LLM text output with markdown fence stripping and repair attempt.
        """
        if not raw_text or not raw_text.strip():
            raise LLMInvalidOutputError("LLM produced an empty response.")

        cleaned = raw_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                raise LLMInvalidOutputError("Parsed LLM JSON is not a dictionary object.")
            return data
        except json.JSONDecodeError:
            # Controlled single repair attempt: extract first and last curly braces
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(cleaned[start:end+1])
                    if isinstance(data, dict):
                        return data
                except json.JSONDecodeError:
                    pass

            raise LLMInvalidOutputError(f"Malformed LLM JSON output: {raw_text[:200]}")

    @classmethod
    def sanitize_and_ground_work_order(
        cls,
        llm_raw_data: Dict[str, Any],
        expected_inspection_id: str,
        expected_image_filename: str,
        expected_image_sha256: str,
        cost_data_available: bool,
        verified_cost: Optional[float] = None,
        verified_downtime_hours: Optional[float] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validates LLM-generated work-order content against authoritative ground truths:
        1. Strips any attempted override of authoritative fields.
        2. Detects and guards against fabricated cost and downtime numbers.
        3. Validates and enforces accurate evidence references.
        """
        warnings: List[str] = []
        sanitized: Dict[str, Any] = {}

        # 1. Strip forbidden authoritative fields
        for field in cls.FORBIDDEN_AUTHORITATIVE_LLM_FIELDS:
            if field in llm_raw_data:
                warnings.append(f"Ignored non-authoritative field '{field}' returned by LLM.")

        # 2. Extract allowed content fields
        sanitized["contextual_summary"] = str(llm_raw_data.get("contextual_summary", "")).strip()
        sanitized["engineering_justification"] = str(llm_raw_data.get("engineering_justification", "")).strip()
        sanitized["recommended_action"] = str(llm_raw_data.get("recommended_action", "")).strip()

        req_methods = llm_raw_data.get("required_inspection_methods")
        if isinstance(req_methods, list):
            sanitized["required_inspection_methods"] = [str(m).strip() for m in req_methods if str(m).strip()]
        else:
            sanitized["required_inspection_methods"] = ["Visual Inspection Sa 2.5"]

        safety_notes = llm_raw_data.get("safety_notes")
        if isinstance(safety_notes, list):
            sanitized["safety_notes"] = [str(s).strip() for s in safety_notes if str(s).strip()]
        else:
            sanitized["safety_notes"] = ["Standard PPE and site isolation precautions required."]

        sanitized["recommended_team"] = str(llm_raw_data.get("recommended_team", "Pipeline Structural Integrity Team")).strip()

        # 3. Cost & Downtime Fabrication Guard
        llm_cost = llm_raw_data.get("estimated_cost")
        llm_downtime = llm_raw_data.get("estimated_downtime_hours")

        if not cost_data_available:
            if llm_cost is not None:
                warnings.append(f"Nullified fabricated cost (${llm_cost}) because historical baseline is unavailable.")
                sanitized["estimated_cost"] = None
            else:
                sanitized["estimated_cost"] = None

            if llm_downtime is not None:
                warnings.append(f"Nullified fabricated downtime ({llm_downtime}h) because historical baseline is unavailable.")
                sanitized["estimated_downtime_hours"] = None
            else:
                sanitized["estimated_downtime_hours"] = None

            sanitized["cost_notes"] = "Historical cost data unavailable; field engineering quote required."
        else:
            sanitized["estimated_cost"] = verified_cost
            sanitized["estimated_downtime_hours"] = verified_downtime_hours
            sanitized["cost_notes"] = str(llm_raw_data.get("cost_notes", f"Based on historical average of ${verified_cost}")).strip()

        # 4. Evidence Reference Grounding Validation
        ev_refs = llm_raw_data.get("evidence_references", {})
        if isinstance(ev_refs, dict):
            ref_insp_id = ev_refs.get("inspection_id")
            ref_img = ev_refs.get("source_image_filename")
            ref_sha = ev_refs.get("source_image_sha256")

            if ref_insp_id and ref_insp_id != expected_inspection_id:
                warnings.append(f"Overrode mismatched LLM inspection reference '{ref_insp_id}' with '{expected_inspection_id}'.")
            if ref_img and ref_img != expected_image_filename:
                warnings.append(f"Overrode mismatched LLM image reference '{ref_img}' with '{expected_image_filename}'.")
            if ref_sha and ref_sha != expected_image_sha256:
                warnings.append(f"Overrode mismatched LLM SHA-256 reference with authoritative hash.")

        # Always enforce verified authoritative evidence references
        sanitized["evidence_references"] = {
            "inspection_id": expected_inspection_id,
            "source_image_filename": expected_image_filename,
            "source_image_sha256": expected_image_sha256,
        }

        return sanitized, warnings

    @classmethod
    def sanitize_investigation_plan_output(
        cls,
        llm_raw_data: Dict[str, Any],
        fallback_plan: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validates that LLM-suggested investigation fields do not contain prompt injections,
        unauthorized risk overrides, plant-control commands, or review bypasses.
        """
        warnings: List[str] = []
        sanitized = dict(fallback_plan)

        # Rejection of prompt injection patterns
        injection_keywords = [
            "ignore previous",
            "disable human review",
            "approve this inspection",
            "set risk to zero",
            "modify plc",
            "scada override",
            "plant control"
        ]

        # Scan text fields
        for field in ("objective", "primary_question"):
            val = llm_raw_data.get(field)
            if val and isinstance(val, str):
                lower_val = val.lower()
                if any(k in lower_val for k in injection_keywords):
                    warnings.append(f"Rejected prompt injection attempt in '{field}'; using deterministic baseline.")
                else:
                    sanitized[field] = val.strip()

        # Enforce that authoritative fields in plan are strictly immutable
        sanitized["authoritative"] = False
        sanitized["constraints"] = [
            "Decision support only: zero automated maintenance execution.",
            "Zero plant-control modification or PLC/SCADA override.",
            "Mandatory human sign-off required prior to technician dispatch."
        ]
        return sanitized, warnings
