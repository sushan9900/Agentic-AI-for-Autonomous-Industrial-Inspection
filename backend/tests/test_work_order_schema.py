"""Unit tests for WorkOrderRecommendation and AgentInspectionDecision schemas (Phase 3B)."""

import pytest
from backend.app.schemas.agent_decision import (
    AgentInspectionDecision,
    WorkOrderRecommendation,
)


def test_work_order_recommendation_schema():
    wo = WorkOrderRecommendation(
        work_order_id="wo-insp-001-ASSET-PL-01",
        inspection_id="insp-001",
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        priority="CRITICAL",
        defect_type="crack",
        severity="CRITICAL",
        risk_level="CRITICAL",
        recommended_action="Execute immediate ultrasonic inspection and wall survey.",
        justification="Significant linear crack indication exceeding critical threshold.",
        required_inspection_methods=["Ultrasonic NDE", "Visual Inspection"],
        estimated_cost=None,
        estimated_downtime_hours=None,
        cost_notes="Historical cost unavailable; quote required.",
        recommended_team="Pipeline Integrity Team",
        safety_notes=["Depressurize line before physical inspection."]
    )
    assert wo.work_order_id == "wo-insp-001-ASSET-PL-01"
    assert wo.priority == "CRITICAL"
    assert wo.status == "PENDING_HUMAN_REVIEW"
    assert wo.estimated_cost is None
    assert wo.cost_notes == "Historical cost unavailable; quote required."


def test_agent_inspection_decision_contract():
    decision = AgentInspectionDecision(
        schema_version="1.0",
        decision_id="dec-insp-001-ASSET-PL-01",
        inspection_id="insp-001",
        asset_id="ASSET-PL-01",
        evidence_reference={"inspection_id": "insp-001", "detections_count": 2},
        risk_assessment={"risk_score": 80, "risk_level": "CRITICAL"},
        operational_decision="URGENT_ENGINEERING_REVIEW",
        decision_rationale="Severe defect telemetry.",
        work_order=None,
        reasoning_trace=[],
        evidence_gaps=["No prior ultrasonic record"],
        warnings=[],
        human_review_required=True
    )
    assert decision.decision_id == "dec-insp-001-ASSET-PL-01"
    assert decision.human_review_required is True
    assert decision.operational_decision == "URGENT_ENGINEERING_REVIEW"
