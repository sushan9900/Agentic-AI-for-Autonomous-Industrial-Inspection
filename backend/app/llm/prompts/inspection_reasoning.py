"""Structured reasoning prompt builder for agentic inspection assessment (Phase 2C)."""

import json
from typing import Any, Dict
from backend.app.schemas.context import HistoricalContext
from backend.app.schemas.decision import InspectionDecision
from vision.schemas.evidence import VisionEvidence


class InspectionPromptBuilder:
    """Constructs structured, grounded reasoning prompts for local LLMs."""

    PROMPT_VERSION = "1.0"

    SYSTEM_INSTRUCTION = (
        "You are an expert Industrial Structural Integrity & Non-Destructive Examination (NDE) Assistant. "
        "Analyze multi-modal visual inspection evidence, historical maintenance logs, and deterministic rule outcomes "
        "to produce a rigorous, auditable assessment and draft work order.\n"
        "STRICT CONSTRAINTS:\n"
        "1. Reason ONLY from the supplied visual evidence, deterministic rule outcomes, and historical context.\n"
        "2. Do NOT invent physical measurements, defect detections, or maintenance logs.\n"
        "3. Do NOT claim certified regulatory compliance (ASME/API) or absolute safety guarantees.\n"
        "4. Every recommendation must be a draft subject to mandatory human inspector sign-off.\n"
        "5. Output valid JSON adhering strictly to the requested schema."
    )

    @classmethod
    def build_prompt(
        cls,
        evidence: VisionEvidence,
        decision: InspectionDecision,
        context: HistoricalContext
    ) -> str:
        """Builds a compact structured prompt string."""
        
        # 1. Visual Evidence Section
        detections_summary = []
        for d in evidence.detections:
            det_info = {
                "id": d.detection_id,
                "type": d.defect_type,
                "confidence": round(d.confidence, 3),
            }
            if d.severity_features:
                aff = getattr(d.severity_features, "affected_area_percentage", None)
                if aff is not None:
                    det_info["area_pct"] = round(aff, 2)
                est_sz = getattr(d.severity_features, "estimated_size", None)
                if est_sz is not None:
                    det_info["size"] = est_sz
            detections_summary.append(det_info)

        # 2. Quality section
        quality_summary = {
            "blur_score": round(evidence.quality.blur_score, 1),
            "warnings": [w.value for w in evidence.quality.warnings]
        }

        # 3. Deterministic Decision Section
        triggered_rules = [
            f"{r.rule_id} ({r.severity.value}): {r.explanation}"
            for r in decision.rule_evaluations if r.triggered
        ]

        # 4. Asset & Component Section
        asset_info = f"{context.asset.name} ({context.asset.asset_type}) at {context.asset.location}"
        comp_info = f"{context.component.name} ({context.component.material})"

        # 5. Maintenance History
        maintenance_logs = [
            f"{m.performed_at.strftime('%Y-%m-%d')} [{m.maintenance_type}]: {m.action_taken}"
            for m in context.maintenance_history[:3]
        ]

        # 6. Prior Inspections
        inspection_logs = [
            f"{i.inspection_timestamp.strftime('%Y-%m-%d')} [{i.inspection_method}]: {i.defect_type} ({i.severity})"
            for i in context.previous_inspections[:3]
        ]

        # 7. Incidents
        incidents = [
            f"{inc.incident_id}: {inc.description} (Root cause: {inc.root_cause})"
            for inc in context.relevant_incidents[:2]
        ]

        provenance_tag = "DEVELOPMENT_SYNTHETIC" if context.is_synthetic_data else "PRODUCTION_VERIFIED"

        prompt = f"""### INDUSTRIAL INSPECTION REASONING TASK
DATA PROVENANCE: {provenance_tag}

### 1. CURRENT INSPECTION EVIDENCE
- Image: {evidence.source_image.filename} (Status: {evidence.status.value})
- Quality: {json.dumps(quality_summary)}
- Detections ({len(evidence.detections)}): {json.dumps(detections_summary)}

### 2. DETERMINISTIC DECISION RULES
- Priority: {decision.priority.value}, Confidence: {decision.confidence.value}
- Triggered Rules: {json.dumps(triggered_rules)}

### 3. ASSET & COMPONENT SPECIFICATIONS
- Asset: {asset_info}
- Component: {comp_info}

### 4. HISTORICAL MAINTENANCE & SERVICE LOGS
{json.dumps(maintenance_logs)}

### 5. PRIOR INSPECTION RECORDS
{json.dumps(inspection_logs)}

### 6. RELEVANT HISTORICAL FAILURE INCIDENTS
{json.dumps(incidents)}

### REQUIRED JSON OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this schema:
{{
  "summary": "Executive summary of visual findings and asset condition",
  "historical_context_summary": "Summary of prior maintenance and defect patterns",
  "reasoning": "Engineering rationale connecting detections, material, and potential failure modes",
  "risk_factors": ["Risk 1", "Risk 2"],
  "recommended_actions": ["Action 1", "Action 2"],
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "uncertainty": "Statement of perception limitations or data gaps",
  "draft_work_order": {{
    "priority": "{decision.priority.value}",
    "recommended_action": "Prescribed draft verification procedure",
    "justification": "Rationale referencing visual detections and component history",
    "required_inspection": "Specific NDE examination method (e.g. Ultrasonic NDE Sa 2.5)",
    "suggested_team": "Pipeline Structural Integrity Team",
    "estimated_downtime_hours": 4.0,
    "estimated_cost": 2500.0,
    "supporting_evidence": ["det-001"],
    "historical_support": ["Prior coating record"]
  }}
}}
"""
        return prompt
