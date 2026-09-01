"""Deterministic decision policy mapping multi-modal evidence and engineering rules to operational decisions (Phase 3B)."""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class DecisionOutcome(BaseModel):
    """Result of evaluating the deterministic decision policy."""
    action: str  # "URGENT_ENGINEERING_REVIEW", "PRIORITY_MAINTENANCE", "PLAN_MAINTENANCE", "SCHEDULE_INSPECTION", "MONITOR", "INSUFFICIENT_EVIDENCE"
    priority: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    rationale: str
    triggered_rules: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class DecisionPolicyEngine:
    """Evaluates combined CV evidence, relational context, engineering thresholds, and risk score."""

    @staticmethod
    def evaluate(
        defect_count: int,
        max_confidence: float,
        max_affected_area_percentage: float,
        max_crack_length_pixels: float,
        risk_score: int,
        risk_level: str,
        triggered_rules: List[str],
        has_critical_component: bool = False,
        recurrence_count: int = 0,
        has_quality_warnings: bool = False,
        evidence_valid: bool = True
    ) -> DecisionOutcome:
        """Determines operational action based on deterministic hierarchy."""
        if not evidence_valid:
            return DecisionOutcome(
                action="INSUFFICIENT_EVIDENCE",
                priority="LOW",
                rationale="Visual perception evidence is invalid or incomplete; cannot formulate operational recommendation.",
                triggered_rules=[]
            )

        # 1. Tier 1: Urgent Engineering Review
        # Triggered by CRITICAL risk band (score >= 75), extensive crack length, or critical rule violations
        if (
            risk_score >= 75
            or risk_level == "CRITICAL"
            or max_crack_length_pixels >= 200.0
            or max_affected_area_percentage >= 4.0
            or any("CRITICAL" in r for r in triggered_rules)
        ):
            return DecisionOutcome(
                action="URGENT_ENGINEERING_REVIEW",
                priority="CRITICAL",
                rationale=(
                    f"Severe defect telemetry detected (Risk Score: {risk_score}, Crack Length: {max_crack_length_pixels:.1f}px, "
                    f"Area: {max_affected_area_percentage:.2f}%). Immediate structural integrity review required."
                ),
                triggered_rules=triggered_rules
            )

        # 2. Tier 2: Priority Maintenance
        # Triggered by HIGH risk band (score >= 50), defect recurrence across inspections, or high confidence detections
        if (
            risk_score >= 50
            or risk_level == "HIGH"
            or recurrence_count >= 2
            or (defect_count > 0 and max_confidence >= 0.75 and max_affected_area_percentage >= 1.5)
        ):
            return DecisionOutcome(
                action="PRIORITY_MAINTENANCE",
                priority="HIGH",
                rationale=(
                    f"High operational risk profile (Risk Score: {risk_score}, Recurrence: {recurrence_count} cycles). "
                    f"Requires expedited maintenance work-order scheduling."
                ),
                triggered_rules=triggered_rules
            )

        # 3. Tier 3: Plan Maintenance
        # Triggered by MEDIUM risk band (score >= 25) or established defect indications
        if (
            risk_score >= 25
            or risk_level == "MEDIUM"
            or (defect_count > 0 and max_confidence >= 0.5)
        ):
            return DecisionOutcome(
                action="PLAN_MAINTENANCE",
                priority="MEDIUM",
                rationale=(
                    f"Moderate defect indication detected (Risk Score: {risk_score}, Defects: {defect_count}). "
                    f"Standard routine maintenance planning recommended."
                ),
                triggered_rules=triggered_rules
            )

        # 4. Tier 4: Schedule Inspection
        # Triggered by marginal confidence (< 0.50), quality warnings, or routine survey interval
        if defect_count > 0 or has_quality_warnings:
            return DecisionOutcome(
                action="SCHEDULE_INSPECTION",
                priority="LOW",
                rationale=(
                    f"Marginal or low-confidence indications observed (Confidence: {max_confidence*100:.1f}%). "
                    f"Follow-up secondary visual inspection survey recommended."
                ),
                triggered_rules=triggered_rules
            )

        # 5. Tier 5: Normal Baseline Monitor
        return DecisionOutcome(
            action="MONITOR",
            priority="LOW",
            rationale="No active defects or anomalous surface features detected. Continue standard monitoring schedule.",
            triggered_rules=[]
        )


# Global decision policy engine instance
decision_policy_engine = DecisionPolicyEngine()
