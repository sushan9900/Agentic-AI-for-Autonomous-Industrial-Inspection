"""Deterministic decision test scenarios covering all authoritative policy classes (Phase 5B)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DecisionCase(BaseModel):
    """Specification of a deterministic decision policy evaluation case."""
    case_id: str
    description: str
    defect_type: str
    defect_count: int
    max_confidence: float
    max_affected_area_percentage: float
    max_crack_length_pixels: float
    risk_score: int
    risk_level: str
    triggered_rules: List[str]
    has_critical_component: bool = False
    recurrence_count: int = 0
    has_quality_warnings: bool = False
    evidence_valid: bool = True
    expected_action: str
    expected_priority: str
    expected_human_review_required: bool

    model_config = ConfigDict(extra="forbid")


def get_evaluation_cases() -> List[DecisionCase]:
    """Generates comprehensive deterministic test scenarios covering all policy classes."""
    return [
        DecisionCase(
            case_id="CASE-01-CRITICAL-DEFECT",
            description="Extensive structural crack exceeding critical length and area thresholds",
            defect_type="crack",
            defect_count=3,
            max_confidence=0.88,
            max_affected_area_percentage=4.55,
            max_crack_length_pixels=250.0,
            risk_score=100,
            risk_level="CRITICAL",
            triggered_rules=["RULE-CRACK-PL-001", "RULE-SEV-CRITICAL-01"],
            has_critical_component=True,
            recurrence_count=1,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="URGENT_ENGINEERING_REVIEW",
            expected_priority="CRITICAL",
            expected_human_review_required=True
        ),
        DecisionCase(
            case_id="CASE-02-HIGH-RISK-RECURRENT",
            description="Recurrent defect across multiple inspection cycles with high confidence",
            defect_type="crack",
            defect_count=2,
            max_confidence=0.82,
            max_affected_area_percentage=2.20,
            max_crack_length_pixels=95.0,
            risk_score=65,
            risk_level="HIGH",
            triggered_rules=["RULE-RECURRENCE-02"],
            has_critical_component=False,
            recurrence_count=2,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="PRIORITY_MAINTENANCE",
            expected_priority="HIGH",
            expected_human_review_required=True
        ),
        DecisionCase(
            case_id="CASE-03-MEDIUM-RISK-ESTABLISHED",
            description="Moderate localized surface indication within routine maintenance planning band",
            defect_type="crack",
            defect_count=1,
            max_confidence=0.68,
            max_affected_area_percentage=0.90,
            max_crack_length_pixels=45.0,
            risk_score=35,
            risk_level="MEDIUM",
            triggered_rules=[],
            has_critical_component=False,
            recurrence_count=0,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="PLAN_MAINTENANCE",
            expected_priority="MEDIUM",
            expected_human_review_required=True
        ),
        DecisionCase(
            case_id="CASE-04-LOW-RISK-MARGINAL",
            description="Marginal confidence defect indication requiring follow-up inspection survey",
            defect_type="crack",
            defect_count=1,
            max_confidence=0.32,
            max_affected_area_percentage=0.15,
            max_crack_length_pixels=18.0,
            risk_score=20,
            risk_level="LOW",
            triggered_rules=[],
            has_critical_component=False,
            recurrence_count=0,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="SCHEDULE_INSPECTION",
            expected_priority="LOW",
            expected_human_review_required=True
        ),
        DecisionCase(
            case_id="CASE-05-NO-DEFECT-MONITOR",
            description="Clear asset surface with zero defects and no quality anomalies",
            defect_type="none",
            defect_count=0,
            max_confidence=0.0,
            max_affected_area_percentage=0.0,
            max_crack_length_pixels=0.0,
            risk_score=15,
            risk_level="LOW",
            triggered_rules=[],
            has_critical_component=False,
            recurrence_count=0,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="MONITOR",
            expected_priority="LOW",
            expected_human_review_required=False
        ),
        DecisionCase(
            case_id="CASE-06-INSUFFICIENT-EVIDENCE",
            description="Corrupt, truncated, or invalid perception evidence payload",
            defect_type="unknown",
            defect_count=0,
            max_confidence=0.0,
            max_affected_area_percentage=0.0,
            max_crack_length_pixels=0.0,
            risk_score=0,
            risk_level="LOW",
            triggered_rules=[],
            has_critical_component=False,
            recurrence_count=0,
            has_quality_warnings=False,
            evidence_valid=False,
            expected_action="INSUFFICIENT_EVIDENCE",
            expected_priority="LOW",
            expected_human_review_required=True
        ),
        DecisionCase(
            case_id="CASE-07-QUALITY-WARNING-INSPECTION",
            description="Zero defects detected but camera blur/lighting quality warning present",
            defect_type="none",
            defect_count=0,
            max_confidence=0.0,
            max_affected_area_percentage=0.0,
            max_crack_length_pixels=0.0,
            risk_score=20,
            risk_level="LOW",
            triggered_rules=[],
            has_critical_component=False,
            recurrence_count=0,
            has_quality_warnings=True,
            evidence_valid=True,
            expected_action="SCHEDULE_INSPECTION",
            expected_priority="LOW",
            expected_human_review_required=True
        ),
        DecisionCase(
            case_id="CASE-08-CRITICAL-COMPONENT-TIER",
            description="High-confidence detection on a critical main hydrocarbon feed line",
            defect_type="crack",
            defect_count=2,
            max_confidence=0.89,
            max_affected_area_percentage=3.10,
            max_crack_length_pixels=180.0,
            risk_score=85,
            risk_level="CRITICAL",
            triggered_rules=["RULE-CRITICAL-ASSET-01"],
            has_critical_component=True,
            recurrence_count=1,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="URGENT_ENGINEERING_REVIEW",
            expected_priority="CRITICAL",
            expected_human_review_required=True
        ),
        DecisionCase(
            case_id="CASE-09-EXTREME-SEVERITY",
            description="Clustered severe defect profile exceeding all engineering tolerance limits",
            defect_type="crack",
            defect_count=5,
            max_confidence=0.96,
            max_affected_area_percentage=7.80,
            max_crack_length_pixels=380.0,
            risk_score=100,
            risk_level="CRITICAL",
            triggered_rules=["RULE-CRACK-PL-001", "RULE-SEV-CRITICAL-01", "RULE-MULTIPLE-01"],
            has_critical_component=True,
            recurrence_count=3,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="URGENT_ENGINEERING_REVIEW",
            expected_priority="CRITICAL",
            expected_human_review_required=True
        ),
        DecisionCase(
            case_id="CASE-10-NON-CRITICAL-LOW-RISK",
            description="Low severity baseline feature on non-critical secondary casing",
            defect_type="none",
            defect_count=0,
            max_confidence=0.0,
            max_affected_area_percentage=0.0,
            max_crack_length_pixels=0.0,
            risk_score=10,
            risk_level="LOW",
            triggered_rules=[],
            has_critical_component=False,
            recurrence_count=0,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="MONITOR",
            expected_priority="LOW",
            expected_human_review_required=False
        ),
        DecisionCase(
            case_id="CASE-11-PRIORITY-MAINTENANCE-THRESHOLD",
            description="Established defect with 0.78 confidence and 1.8% area triggering Tier 2",
            defect_type="crack",
            defect_count=1,
            max_confidence=0.78,
            max_affected_area_percentage=1.80,
            max_crack_length_pixels=60.0,
            risk_score=50,
            risk_level="HIGH",
            triggered_rules=[],
            has_critical_component=False,
            recurrence_count=0,
            has_quality_warnings=False,
            evidence_valid=True,
            expected_action="PRIORITY_MAINTENANCE",
            expected_priority="HIGH",
            expected_human_review_required=True
        )
    ]
