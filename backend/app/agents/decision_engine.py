"""Deterministic Decision Engine implementing rule aggregation and auditable decision generation."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.agents.contracts import BaseDecisionEngine
from backend.app.schemas.decision import (
    DecisionConfidence,
    DecisionTraceStep,
    EvidenceReference,
    InspectionDecision,
    InspectionPriority,
    RuleEvaluation,
)
from backend.app.services.decision.evidence_adapter import EvidenceAdapter, NormalizedInspectionEvidence
from backend.app.services.decision.rule_engine import InspectionRuleEngine
from vision.schemas.evidence import InspectionStatus, VisionEvidence

PRIORITY_PRECEDENCE_ORDER = [
    InspectionPriority.CRITICAL,
    InspectionPriority.HIGH,
    InspectionPriority.REVIEW_REQUIRED,
    InspectionPriority.MEDIUM,
    InspectionPriority.LOW,
]

STANDARD_LIMITATIONS = [
    "Development baseline model detects crack anomalies only; corrosion and other defects are not evaluated.",
    "Thresholds are for research/development testing and do not constitute certified engineering limits (API/ASME).",
    "Clean visual evidence does not guarantee structural integrity under internal or subsurface failure modes.",
    "All high-priority and critical recommendations require mandatory human inspector sign-off before dispatch."
]


class DeterministicDecisionEngine(BaseDecisionEngine):
    """Deterministic, provider-independent inspection decision engine."""

    def __init__(self, rule_engine: Optional[InspectionRuleEngine] = None):
        self.rule_engine = rule_engine or InspectionRuleEngine()

    def evaluate(
        self,
        evidence: VisionEvidence,
        decision_id: Optional[str] = None
    ) -> InspectionDecision:
        """
        Executes deterministic evaluation pipeline on VisionEvidence contract.
        """
        trace: List[DecisionTraceStep] = []
        step_idx = 1

        # Step 1: Evidence Validation & Ingestion
        t_ingest = datetime.now(timezone.utc).isoformat()
        trace.append(DecisionTraceStep(
            step_number=step_idx,
            action="INGEST_EVIDENCE",
            inputs_used={
                "inspection_id": evidence.inspection_id,
                "schema_version": evidence.schema_version,
                "status": evidence.status.value,
                "source_image": evidence.source_image.filename
            },
            output_summary=f"Ingested VisionEvidence v{evidence.schema_version} with status {evidence.status.value}.",
            timestamp=t_ingest
        ))
        step_idx += 1

        # Step 2: Evidence Normalization & Quality Invariant Check
        normalized: NormalizedInspectionEvidence = EvidenceAdapter.adapt(evidence)
        t_adapt = datetime.now(timezone.utc).isoformat()
        trace.append(DecisionTraceStep(
            step_number=step_idx,
            action="NORMALIZE_EVIDENCE",
            inputs_used={
                "detection_count": normalized.detection_count,
                "max_affected_area_pct": normalized.max_affected_area_pct,
                "quality_warnings_count": len(normalized.quality_warnings)
            },
            output_summary=f"Normalized evidence: {normalized.detection_count} detection(s), {len(normalized.quality_warnings)} quality warning(s).",
            timestamp=t_adapt
        ))
        step_idx += 1

        # Step 3: Rule Evaluation
        rule_evaluations: List[RuleEvaluation] = self.rule_engine.evaluate(normalized)
        triggered_rules = [r for r in rule_evaluations if r.triggered]
        t_rule = datetime.now(timezone.utc).isoformat()
        trace.append(DecisionTraceStep(
            step_number=step_idx,
            action="EVALUATE_RULES",
            inputs_used={"total_rules_evaluated": len(rule_evaluations)},
            output_summary=f"Evaluated {len(rule_evaluations)} rules ({len(triggered_rules)} triggered: {[r.rule_id for r in triggered_rules]}).",
            timestamp=t_rule
        ))
        step_idx += 1

        # Step 4: Deterministic Priority Aggregation
        aggregated_priority = InspectionPriority.LOW
        for candidate_priority in PRIORITY_PRECEDENCE_ORDER:
            # Check if any triggered rule matches candidate priority
            if any(r.triggered and r.severity == candidate_priority for r in rule_evaluations):
                aggregated_priority = candidate_priority
                break

        # Step 5: Confidence & Review Requirements Determination
        has_quality_warnings = len(normalized.quality_warnings) > 0
        min_conf = normalized.min_confidence or 1.0

        if has_quality_warnings or (normalized.detection_count > 0 and min_conf < 0.35):
            confidence = DecisionConfidence.LOW
        elif min_conf < 0.60 or normalized.detection_count == 0:
            confidence = DecisionConfidence.MEDIUM
        else:
            confidence = DecisionConfidence.HIGH

        requires_review = (
            aggregated_priority in (InspectionPriority.CRITICAL, InspectionPriority.HIGH, InspectionPriority.REVIEW_REQUIRED)
            or confidence == DecisionConfidence.LOW
            or has_quality_warnings
        )

        # Step 6: Textual Summaries Synthesis
        if normalized.detection_count == 0:
            defect_summary = "No defect indications detected above active confidence threshold in visual evidence."
        else:
            defect_summary = (
                f"Detected {normalized.detection_count} crack indication(s) with maximum surface coverage of "
                f"{normalized.max_affected_area_pct or 0.0:.2f}% and estimated maximum crack length of "
                f"{normalized.max_crack_length_px or 0.0:.1f}px."
            )

        warn_str = f" Flagged with {len(normalized.quality_warnings)} quality warning(s)." if has_quality_warnings else " Image quality metrics passed."
        evidence_summary = (
            f"Inspection executed via {evidence.model.model_name} (checkpoint hash: {evidence.model.checkpoint_sha256[:8]}). "
            f"Image hash: {evidence.source_image.sha256_hash[:8]}.{warn_str}"
        )

        # Step 7: Recommended Action Mapping
        if aggregated_priority == InspectionPriority.CRITICAL:
            rec_action = "IMMEDIATE ACTION REQUIRED: Flag for emergency structural integrity review and non-destructive examination (NDE)."
        elif aggregated_priority == InspectionPriority.HIGH:
            rec_action = "EXPEDITED ACTION: Schedule expedited physical inspection and ultrasonic thickness testing within 48 hours."
        elif aggregated_priority == InspectionPriority.REVIEW_REQUIRED:
            rec_action = "REVIEW REQUIRED: Visual evidence degraded or model confidence marginal. Qualified inspector verification mandatory before disposition."
        elif aggregated_priority == InspectionPriority.MEDIUM:
            rec_action = "SCHEDULED MONITORING: Log defect coordinates for routine ultrasonic / visual re-inspection during next planned maintenance cycle."
        else:
            rec_action = "NORMAL MONITORING: No actionable anomalies detected. Maintain standard scheduled maintenance inspection cycle."

        t_agg = datetime.now(timezone.utc).isoformat()
        trace.append(DecisionTraceStep(
            step_number=step_idx,
            action="AGGREGATE_DECISION",
            inputs_used={
                "triggered_severities": [r.severity.value for r in triggered_rules],
                "aggregated_priority": aggregated_priority.value,
                "confidence": confidence.value
            },
            output_summary=f"Final priority determined as {aggregated_priority.value} with {confidence.value} confidence.",
            timestamp=t_agg
        ))

        # References
        references = EvidenceReference(
            source_image_filename=evidence.source_image.filename,
            source_image_sha256=evidence.source_image.sha256_hash,
            model_checkpoint_sha256=evidence.model.checkpoint_sha256,
            detection_ids=normalized.detection_ids
        )

        final_decision_id = decision_id or f"dec-{evidence.inspection_id}-{evidence.source_image.sha256_hash[:8]}"

        return InspectionDecision(
            decision_id=final_decision_id,
            schema_version="1.0",
            inspection_id=evidence.inspection_id,
            priority=aggregated_priority,
            confidence=confidence,
            defect_summary=defect_summary,
            evidence_summary=evidence_summary,
            recommended_action=rec_action,
            requires_human_review=requires_review,
            rule_evaluations=rule_evaluations,
            evidence_references=references,
            decision_trace=trace,
            limitations=STANDARD_LIMITATIONS
        )
