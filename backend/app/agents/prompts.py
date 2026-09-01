"""Evidence-driven prompt templates and builders for local LLM reasoning (Phase 3B)."""

import json
from typing import Any, Dict, List, Optional
from vision.schemas.evidence import VisionEvidence


class AgentPromptBuilder:
    """Constructs structured, evidence-grounded prompts for Ollama (Gemma 3)."""

    PROMPT_VERSION = "2.0-agentic-decision"

    SYSTEM_INSTRUCTION = (
        "You are an expert autonomous industrial structural integrity inspection decision agent.\n"
        "Your role is to interpret structured visual evidence, relational asset intelligence, and deterministic "
        "engineering thresholds to formulate a rigorous maintenance work-order draft.\n\n"
        "CRITICAL OPERATIONAL RULES:\n"
        "1. DO NOT invent or fabricate missing maintenance records, costs, or downtime hours. If historical cost is unavailable, set cost to null.\n"
        "2. DO NOT grant structural safety certifications or bypass human engineering authorization.\n"
        "3. Every work order draft requires explicit human inspector authorization (PENDING_HUMAN_REVIEW).\n"
        "4. Output MUST be strictly valid JSON adhering to the specified schema without conversational prose or markdown formatting."
    )

    @classmethod
    def build_prompt(
        cls,
        evidence: VisionEvidence,
        asset_context: Dict[str, Any],
        maintenance_history: List[Dict[str, Any]],
        severity_thresholds: List[Dict[str, Any]],
        similar_incidents: List[Dict[str, Any]],
        risk_assessment: Dict[str, Any],
        operational_decision: str
    ) -> str:
        """Constructs the complete evidence package prompt."""
        detections_summary = [
            {
                "detection_id": d.detection_id,
                "defect_type": d.defect_type.value if hasattr(d.defect_type, "value") else str(d.defect_type),
                "confidence": round(d.confidence, 3),
                "affected_area_percentage": getattr(d.severity_features, "affected_area_percentage", None) if d.severity_features else None,
                "crack_length_pixels": getattr(d.severity_features, "crack_length_pixels", None) if d.severity_features else None,
                "location_type": getattr(d.severity_features, "location_type", None) if d.severity_features else None,
            }
            for d in evidence.detections
        ]

        # Check for historical cost/downtime references
        historical_costs = [m.get("cost") for m in maintenance_history if m.get("cost") is not None]
        historical_downtimes = [m.get("downtime_hours") for m in maintenance_history if m.get("downtime_hours") is not None]
        avg_hist_cost = round(sum(historical_costs) / len(historical_costs), 2) if historical_costs else None
        avg_hist_downtime = round(sum(historical_downtimes) / len(historical_downtimes), 1) if historical_downtimes else None

        prompt_payload = {
            "evidence_package": {
                "inspection_id": evidence.inspection_id,
                "source_image_filename": evidence.source_image.filename,
                "detection_count": len(evidence.detections),
                "detections": detections_summary,
                "quality_warnings": [
                    q.value if hasattr(q, "value") else str(q)
                    for q in (getattr(evidence, "quality", None).warnings if getattr(evidence, "quality", None) else [])
                ],
            },
            "asset_intelligence": {
                "asset_id": asset_context.get("asset_id"),
                "asset_code": asset_context.get("asset_code"),
                "asset_type": asset_context.get("asset_type"),
                "location": asset_context.get("location"),
                "operational_status": asset_context.get("operational_status"),
                "service_age_years": asset_context.get("service_age_years"),
                "warranty_status": asset_context.get("warranty_status"),
            },
            "historical_maintenance": maintenance_history[:5],
            "engineering_thresholds_triggered": severity_thresholds,
            "similar_incidents_precedents": similar_incidents[:3],
            "deterministic_risk_assessment": {
                "risk_score": risk_assessment.get("risk_score"),
                "risk_level": risk_assessment.get("risk_level"),
                "contributing_factors": risk_assessment.get("contributing_factors"),
            },
            "authoritative_operational_decision": operational_decision,
            "historical_baseline_estimates": {
                "available_cost": avg_hist_cost,
                "available_downtime_hours": avg_hist_downtime
            }
        }

        return f"""### INDUSTRIAL INSPECTION EVIDENCE & CONTEXT PACKAGE:
{json.dumps(prompt_payload, indent=2, default=str)}

### INSTRUCTIONS:
Based strictly on the provided evidence package above, generate a detailed maintenance recommendation JSON adhering to this exact JSON schema:
{{
  "contextual_summary": "Executive summary synthesizing visual evidence, asset context, and historical records",
  "engineering_justification": "Technical engineering rationale detailing defect mechanisms, stress implications, and risk factors",
  "recommended_action": "Actionable, precise engineering maintenance instruction",
  "required_inspection_methods": ["Specific NDE / testing method 1", "Specific NDE / testing method 2"],
  "safety_notes": ["Safety note or hazard mitigation 1", "Safety note 2"],
  "estimated_cost": {avg_hist_cost if avg_hist_cost is not None else "null"},
  "estimated_downtime_hours": {avg_hist_downtime if avg_hist_downtime is not None else "null"},
  "cost_notes": "{f'Based on historical maintenance average of ${avg_hist_cost}' if avg_hist_cost else 'Historical cost data unavailable; field engineering quote required.'}",
  "recommended_team": "Pipeline Structural Integrity Team"
}}

Respond with the JSON object only.
"""
