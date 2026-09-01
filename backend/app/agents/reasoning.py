"""Reasoning response parser and validation helpers (Phase 2C)."""

import json
from typing import Any, Dict, Tuple
from backend.app.agents.work_order import WorkOrderSynthesizer
from backend.app.schemas.agent_assessment import AgentInspectionAssessment, DraftWorkOrder
from backend.app.schemas.context import HistoricalContext
from backend.app.schemas.decision import InspectionDecision
from vision.schemas.evidence import VisionEvidence


class ReasoningParserError(Exception):
    """Exception raised when LLM reasoning response cannot be validated."""
    pass


class ReasoningParser:
    """Parses and validates LLM generation output into typed Pydantic contracts."""

    @staticmethod
    def parse_llm_response(
        raw_text: str,
        assessment_id: str,
        draft_id: str,
        evidence: VisionEvidence,
        decision: InspectionDecision,
        context: HistoricalContext,
        model_provenance: Dict[str, Any]
    ) -> Tuple[AgentInspectionAssessment, DraftWorkOrder]:
        """
        Parses JSON response from LLM and validates against AgentInspectionAssessment and DraftWorkOrder.
        """
        cleaned_text = raw_text.strip()
        # Strip markdown codeblocks if present
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        try:
            parsed = json.loads(cleaned_text)
        except Exception as e:
            raise ReasoningParserError(f"Failed to parse LLM response as JSON: {str(e)}\nRaw Response: {raw_text[:200]}") from e

        # Extract assessment fields with validation
        summary = parsed.get("summary") or decision.defect_summary
        historical_summary = parsed.get("historical_context_summary") or f"Component {context.component.component_id} installed on {context.asset.name}."
        reasoning_text = parsed.get("reasoning") or decision.evidence_summary
        risk_factors = parsed.get("risk_factors") or [f"Physical defect propagation under service pressure.", "Potential localized fatigue."]
        recommended_actions = parsed.get("recommended_actions") or [decision.recommended_action]
        confidence = parsed.get("confidence") or decision.confidence.value
        uncertainty = parsed.get("uncertainty") or "Assessment is based on visual perception and historical maintenance records."

        # Verified detections
        detected_defects = [
            {
                "detection_id": d.detection_id,
                "defect_type": d.defect_type,
                "confidence": d.confidence,
                "affected_area_percentage": d.severity_features.affected_area_percentage if d.severity_features else None
            }
            for d in evidence.detections
        ]

        source_refs = {
            "source_image_filename": evidence.source_image.filename,
            "source_image_sha256": evidence.source_image.sha256_hash,
            "model_checkpoint_sha256": evidence.model.checkpoint_sha256,
            "inspection_decision_id": decision.decision_id,
            "is_synthetic_data": context.is_synthetic_data,
            "component_id": context.component.component_id,
            "asset_id": context.asset.asset_id
        }

        assessment = AgentInspectionAssessment(
            schema_version="1.0",
            assessment_id=assessment_id,
            component_id=context.component.component_id,
            inspection_reference=evidence.inspection_id,
            summary=summary,
            detected_defects=detected_defects,
            historical_context_summary=historical_summary,
            reasoning=reasoning_text,
            risk_factors=risk_factors if isinstance(risk_factors, list) else [str(risk_factors)],
            recommended_actions=recommended_actions if isinstance(recommended_actions, list) else [str(recommended_actions)],
            confidence=str(confidence).upper() if str(confidence).upper() in ("LOW", "MEDIUM", "HIGH") else decision.confidence.value,
            uncertainty=str(uncertainty),
            human_review_required=True,  # Safety invariant
            source_references=source_refs,
            model_provenance=model_provenance
        )

        # Extract draft work order
        dwo_dict = parsed.get("draft_work_order", {})
        draft_work_order = WorkOrderSynthesizer.create_draft(
            draft_id=draft_id,
            component_id=context.component.component_id,
            inspection_reference=evidence.inspection_id,
            priority=dwo_dict.get("priority", decision.priority.value),
            recommended_action=dwo_dict.get("recommended_action", decision.recommended_action),
            justification=dwo_dict.get("justification", f"Detections in visual evidence require verification: {summary}"),
            required_inspection=dwo_dict.get("required_inspection", "Ultrasonic Non-Destructive Examination (NDE) Sa 2.5"),
            suggested_team=dwo_dict.get("suggested_team", "Pipeline Structural Integrity Team"),
            estimated_downtime_hours=float(dwo_dict.get("estimated_downtime_hours", 4.0)) if dwo_dict.get("estimated_downtime_hours") is not None else None,
            estimated_cost=float(dwo_dict.get("estimated_cost", 2500.0)) if dwo_dict.get("estimated_cost") is not None else None,
            supporting_evidence=[d.detection_id for d in evidence.detections],
            historical_support=[m.maintenance_id for m in context.maintenance_history[:2]],
            uncertainty=dwo_dict.get("uncertainty", uncertainty)
        )

        return assessment, draft_work_order
