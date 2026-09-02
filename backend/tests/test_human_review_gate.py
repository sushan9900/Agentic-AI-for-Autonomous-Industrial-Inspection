"""Unit tests verifying the Human-in-the-Loop review gate integrity (Phase 5B)."""

import pytest
from backend.app.agents.decision_policy import DecisionPolicyEngine
from backend.app.database.session import SessionLocal
from backend.app.schemas.agent_decision import AgentInspectionDecision, WorkOrderRecommendation
from backend.app.services.agent import (
    DecisionNotFoundError,
    InvalidReviewActionError,
    agent_decision_service,
)


@pytest.fixture
def policy_engine():
    return DecisionPolicyEngine()


def test_human_review_enforced_on_critical_action(policy_engine):
    outcome = policy_engine.evaluate(
        defect_count=2,
        max_confidence=0.88,
        max_affected_area_percentage=4.5,
        max_crack_length_pixels=220.0,
        risk_score=90,
        risk_level="CRITICAL",
        triggered_rules=["RULE-CRACK-PL-001"]
    )
    assert outcome.action == "URGENT_ENGINEERING_REVIEW"
    # Action must enforce human review
    assert outcome.action != "MONITOR"


def test_initial_review_status_is_pending():
    wo = WorkOrderRecommendation(
        work_order_id="wo-test-gate-01",
        inspection_id="insp-gate-01",
        asset_id="ASSET-PL-01",
        priority="HIGH",
        defect_type="crack",
        severity="HIGH",
        risk_level="HIGH",
        recommended_action="Expedited NDE Survey",
        justification="High risk defect observed."
    )
    assert wo.status == "PENDING_HUMAN_REVIEW"


def test_no_automated_dispatch_execution():
    """Verifies that creating a decision never dispatches technicians or executes work."""
    decision = AgentInspectionDecision(
        decision_id="dec-gate-test-01",
        inspection_id="insp-gate-01",
        asset_id="ASSET-PL-01",
        evidence_reference={"detections_count": 1},
        risk_assessment={"risk_score": 60, "risk_level": "HIGH"},
        operational_decision="PRIORITY_MAINTENANCE",
        decision_rationale="High risk profile.",
        human_review_required=True,
        review_status="PENDING_HUMAN_REVIEW"
    )

    assert decision.review_status == "PENDING_HUMAN_REVIEW"
    assert decision.reviewer_name is None
    assert decision.reviewed_at is None


def test_review_action_persistence_and_rejection():
    db = SessionLocal()
    dec_id = "dec-test-gate-review-01"
    try:
        decision = AgentInspectionDecision(
            decision_id=dec_id,
            inspection_id="insp-gate-02",
            asset_id="ASSET-PL-01",
            evidence_reference={"detections_count": 1},
            risk_assessment={"risk_score": 60, "risk_level": "HIGH"},
            operational_decision="PRIORITY_MAINTENANCE",
            decision_rationale="High risk profile.",
            human_review_required=True,
            review_status="PENDING_HUMAN_REVIEW"
        )
        agent_decision_service.save_decision(db=db, decision=decision)

        # Apply valid approval
        reviewed = agent_decision_service.apply_review(
            db=db,
            decision_id=dec_id,
            reviewer_name="Inspector S. Ray",
            review_action="APPROVED",
            review_comment="Approved with NDE instructions."
        )
        assert reviewed.review_status == "APPROVED"
        assert reviewed.reviewer_name == "Inspector S. Ray"

        # Invalid action should raise InvalidReviewActionError
        with pytest.raises(InvalidReviewActionError):
            agent_decision_service.apply_review(
                db=db,
                decision_id=dec_id,
                reviewer_name="Inspector S. Ray",
                review_action="AUTOMATICALLY_DISPATCH"
            )

    finally:
        from backend.app.database.models.agent_decision import AgentDecisionModel
        db.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == dec_id).delete()
        db.commit()
        db.close()
