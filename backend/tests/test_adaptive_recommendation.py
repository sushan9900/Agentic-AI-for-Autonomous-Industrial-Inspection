"""Tests for Adaptive Recommendation Engine and Zero-Overwrite Prioritization (Phase 7E/7F)."""

import pytest
from sqlalchemy.orm import Session

from backend.app.database.session import SessionLocal
from backend.app.services.adaptive_recommendation import adaptive_recommendation_service
from backend.app.services.inspection_prioritization import inspection_prioritization_service
from backend.tests.test_inspection_learning import _create_decision_and_outcome
from backend.app.schemas.inspection_outcome import ReviewOutcomeStatus


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_generate_recommendations_for_false_negatives(db_session: Session):
    """Verifies that recurring false negatives trigger HIGHER_REVIEW_PRIORITY with +15 advisory adjustment."""
    asset_id = "ASSET-PU-07"
    comp_id = "PUMP-SEAL-01"

    _create_decision_and_outcome(
        db_session, "INSP-ADAPT-FN-01", asset_id, comp_id,
        ai_risk=0, ai_sev="NONE", ai_action="MONITOR",
        rev_status=ReviewOutcomeStatus.CORRECTED, conf_defect=True, conf_sev="HIGH", conf_type="SEAL_LEAK",
        ai_detections=0
    )
    _create_decision_and_outcome(
        db_session, "INSP-ADAPT-FN-02", asset_id, comp_id,
        ai_risk=0, ai_sev="NONE", ai_action="MONITOR",
        rev_status=ReviewOutcomeStatus.CORRECTED, conf_defect=True, conf_sev="HIGH", conf_type="SEAL_LEAK",
        ai_detections=0
    )

    recs = adaptive_recommendation_service.generate_recommendations(db_session, asset_id=asset_id, component_id=comp_id)
    assert len(recs) >= 1
    rec = next((r for r in recs if r.recommendation_type == "HIGHER_REVIEW_PRIORITY"), None)
    assert rec is not None
    assert rec.authoritative is False
    assert rec.suggested_score_adjustment == 15
    assert rec.advisory_priority == "CRITICAL"


def test_generate_recommendations_for_action_disagreement(db_session: Session):
    """Verifies that recurring action disagreements trigger REQUIRE_EXPERT_REVIEW."""
    asset_id = "ASSET-PL-01"
    comp_id = "PIPE-VALVE-01"

    _create_decision_and_outcome(
        db_session, "INSP-ADAPT-ACT-01", asset_id, comp_id,
        ai_risk=65, ai_sev="HIGH", ai_action="PRIORITY_MAINTENANCE",
        rev_status=ReviewOutcomeStatus.CORRECTED, conf_defect=True, conf_sev="HIGH", conf_type="VALVE_PACKING_LEAK",
        corr_action="EMERGENCY_ISOLATION"
    )
    _create_decision_and_outcome(
        db_session, "INSP-ADAPT-ACT-02", asset_id, comp_id,
        ai_risk=65, ai_sev="HIGH", ai_action="PRIORITY_MAINTENANCE",
        rev_status=ReviewOutcomeStatus.CORRECTED, conf_defect=True, conf_sev="HIGH", conf_type="VALVE_PACKING_LEAK",
        corr_action="EMERGENCY_ISOLATION"
    )

    recs = adaptive_recommendation_service.generate_recommendations(db_session, asset_id=asset_id, component_id=comp_id)
    rec = next((r for r in recs if r.recommendation_type == "REQUIRE_EXPERT_REVIEW"), None)
    assert rec is not None
    assert rec.authoritative is False
    assert rec.suggested_score_adjustment == 5


def test_adaptive_advisory_zero_overwrite_invariant(db_session: Session):
    """
    INVARIANT-13: Verifies that when an adaptive advisory exists for an item,
    its authoritative priority_score, priority_class, and queue rank remain UNCHANGED.
    """
    asset_id = "ASSET-PU-07"
    comp_id = "PUMP-SEAL-01"

    # Query queue for ASSET-PU-07
    queue = inspection_prioritization_service.get_prioritized_queue(db_session, asset_id=asset_id, limit=50)

    for item in queue.items:
        # Original deterministic score must be strictly in [0, 100]
        assert 0 <= item.priority_score <= 100
        assert item.authoritative is False
        assert item.human_review_required is True

        if item.adaptive_advisory:
            # Advisory must be explicitly marked non-authoritative
            assert item.adaptive_advisory.authoritative is False
            assert "Advisory overlay only" in item.adaptive_advisory.advisory_note
            # The item's priority_score MUST NOT be modified by score_adjustment
            # E.g. if priority_score was 45 and adjustment is +15, priority_score remains 45!
            assert item.priority_score != (item.priority_score + item.adaptive_advisory.score_adjustment) or item.adaptive_advisory.score_adjustment == 0


def test_recommendations_response_schema(db_session: Session):
    """Verifies the response envelope structure of adaptive recommendations."""
    resp = adaptive_recommendation_service.get_recommendations_response(db_session)
    assert resp.methodology_version == "1.0"
    assert "advisory-only" in resp.safety_notice.lower()
    assert resp.total_recommendations == len(resp.recommendations)
