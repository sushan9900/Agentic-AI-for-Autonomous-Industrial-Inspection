"""Tests for Evidence Request Planner (Phase 8E)."""

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.database.session import SessionLocal
from backend.app.schemas.evidence_request import EvidenceRequestType
from backend.app.services.evidence_request_planner import (
    InspectionDecisionNotFoundError,
    evidence_request_planner,
)


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def _create_decision(db: Session, inspection_id: str, gaps: list, detections: list = None):
    dec_id = f"dec-{inspection_id}"
    db.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == dec_id).delete()
    db.commit()

    decision = AgentDecisionModel(
        decision_id=dec_id,
        inspection_id=inspection_id,
        asset_id="ASSET-PL-01",
        operational_decision="PRIORITY_MAINTENANCE",
        risk_score=75,
        risk_level="HIGH",
        decision_rationale="Decision rationale",
        human_review_required=True,
        review_status="PENDING_HUMAN_REVIEW",
        evidence_reference={
            "inspection_id": inspection_id,
            "component_id": "PIPE-SEG-4021",
            "detections": detections or []
        },
        risk_assessment={"risk_score": 75, "risk_level": "HIGH"},
        work_order=None,
        warnings=[],
        evidence_gaps=gaps,
        execution_metrics={"investigation_plan": {"unobserved_gaps": gaps}}
    )
    db.add(decision)
    db.commit()
    return decision


def test_depth_gap_triggers_closeup(db_session: Session):
    """Verifies that depth or wall thickness gaps map to COMPONENT_CLOSEUP."""
    insp_id = "INSP-EVID-DEPTH-01"
    _create_decision(db_session, insp_id, gaps=["Unmeasured crack depth on inner wall"])

    plan = evidence_request_planner.plan_evidence_requests(db_session, insp_id)
    assert plan.total_requests >= 1
    req = next((r for r in plan.requests if r.request_type == EvidenceRequestType.COMPONENT_CLOSEUP), None)
    assert req is not None
    assert req.human_approval_required is True
    assert req.required is True


def test_low_confidence_triggers_higher_resolution(db_session: Session):
    """Verifies that low confidence detection triggers HIGHER_RESOLUTION_IMAGE."""
    insp_id = "INSP-EVID-CONF-01"
    _create_decision(
        db_session,
        insp_id,
        gaps=[],
        detections=[{"defect_type": "CRACK", "confidence": 0.45}]
    )

    plan = evidence_request_planner.plan_evidence_requests(db_session, insp_id)
    assert plan.total_requests >= 1
    req = next((r for r in plan.requests if r.request_type == EvidenceRequestType.HIGHER_RESOLUTION_IMAGE), None)
    assert req is not None
    assert req.human_approval_required is True


def test_missing_decision_raises_error(db_session: Session):
    """Verifies that planning for non-existent inspection raises error."""
    with pytest.raises(InspectionDecisionNotFoundError):
        evidence_request_planner.plan_evidence_requests(db_session, "NON-EXISTENT-INSP-ID")
