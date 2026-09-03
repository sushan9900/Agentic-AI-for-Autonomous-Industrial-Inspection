"""Tests for Inspection Task Recommender (Phase 8C)."""

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.database.models.asset import Asset
from backend.app.database.session import SessionLocal
from backend.app.schemas.task_recommendation import RecommendationType
from backend.app.services.inspection_task_recommender import inspection_task_recommender


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    # Ensure asset exists
    asset = session.query(Asset).filter(Asset.asset_id == "ASSET-PL-01").first()
    if not asset:
        asset = Asset(
            asset_id="ASSET-PL-01",
            name="Crude Hydrocarbon Transmission Pipeline Loop 1A",
            asset_type="PIPELINE",
            location="Unit 4",
            criticality="CRITICAL"
        )
        session.add(asset)
        session.commit()
    yield session
    session.close()


def _create_test_decision(
    db: Session,
    inspection_id: str,
    asset_id: str = "ASSET-PL-01",
    risk_score: int = 85,
    trends: dict = None,
    gaps: list = None
):
    dec_id = f"dec-{inspection_id}"
    db.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == dec_id).delete()
    db.commit()

    decision = AgentDecisionModel(
        decision_id=dec_id,
        inspection_id=inspection_id,
        asset_id=asset_id,
        operational_decision="URGENT_ENGINEERING_REVIEW",
        risk_score=risk_score,
        risk_level="CRITICAL" if risk_score >= 80 else "HIGH",
        decision_rationale="Decision rationale",
        human_review_required=True,
        review_status="PENDING_HUMAN_REVIEW",
        evidence_reference={"inspection_id": inspection_id, "detections_count": 1, "component_id": "PIPE-SEG-4021"},
        risk_assessment={"risk_score": risk_score, "risk_level": "CRITICAL"},
        work_order=None,
        warnings=[],
        evidence_gaps=gaps or [],
        execution_metrics={
            "inspection_trends": trends or {},
            "investigation_plan": {"unobserved_gaps": gaps or []}
        }
    )
    db.add(decision)
    db.commit()
    return decision


def test_recommendation_for_evidence_gaps(db_session: Session):
    """Verifies that missing evidence gaps trigger REQUEST_ADDITIONAL_EVIDENCE."""
    insp_id = "INSP-REC-GAP-01"
    _create_test_decision(db_session, insp_id, gaps=["GAP-01-DEFECT-DEPTH"])

    recs = inspection_task_recommender.generate_recommendations(db_session, asset_id="ASSET-PL-01")
    target_rec = next((r for r in recs if r.inspection_id == insp_id), None)
    assert target_rec is not None
    assert target_rec.recommendation_type == RecommendationType.REQUEST_ADDITIONAL_EVIDENCE
    assert target_rec.authoritative is False
    assert target_rec.human_approval_required is True


def test_recommendation_for_deteriorating_defect(db_session: Session):
    """Verifies that active deterioration triggers REPEAT_INSPECTION."""
    insp_id = "INSP-REC-DET-01"
    _create_test_decision(
        db_session, insp_id, risk_score=85,
        trends={"deterioration_status": "DETERIORATING", "evidence_sufficiency": "SUFFICIENT"}
    )

    recs = inspection_task_recommender.generate_recommendations(db_session, asset_id="ASSET-PL-01")
    target_rec = next((r for r in recs if r.inspection_id == insp_id), None)
    assert target_rec is not None
    assert target_rec.recommendation_type == RecommendationType.REPEAT_INSPECTION
    assert target_rec.urgency == "CRITICAL"


def test_recommendation_for_pending_review(db_session: Session):
    """Verifies that pending decision without gaps triggers REVIEW_EXISTING_INSPECTION."""
    insp_id = "INSP-REC-REV-01"
    _create_test_decision(
        db_session, insp_id, risk_score=75,
        trends={"deterioration_status": "STABLE", "evidence_sufficiency": "SUFFICIENT"}
    )

    recs = inspection_task_recommender.generate_recommendations(db_session, asset_id="ASSET-PL-01")
    target_rec = next((r for r in recs if r.inspection_id == insp_id), None)
    assert target_rec is not None
    assert target_rec.recommendation_type == RecommendationType.REVIEW_EXISTING_INSPECTION


def test_recommendations_response_envelope(db_session: Session):
    """Verifies standard response envelope and safety disclaimer."""
    resp = inspection_task_recommender.get_recommendations_response(db_session, asset_id="ASSET-PL-01")
    assert resp.methodology_version == "1.0"
    assert "advisory-only" in resp.safety_notice.lower()
    assert resp.total_recommendations == len(resp.recommendations)
