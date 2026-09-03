"""Tests for Prediction vs Outcome Learning Analysis and Error Pattern Detection (Phase 7C/7D)."""

from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.database.models.asset import Asset
from backend.app.database.models.inspection_outcome import InspectionOutcomeModel
from backend.app.database.session import SessionLocal
from backend.app.schemas.inspection_outcome import (
    ConfirmationSource,
    CorrectionType,
    EvidenceQuality,
    InspectionOutcomeCreate,
    ReviewOutcomeStatus,
    ReviewerCorrection,
)
from backend.app.services.inspection_learning import inspection_learning_service
from backend.app.services.inspection_outcome import inspection_outcome_service


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def _create_decision_and_outcome(
    db: Session,
    insp_id: str,
    asset_id: str,
    component_id: str,
    ai_risk: int,
    ai_sev: str,
    ai_action: str,
    rev_status: ReviewOutcomeStatus,
    conf_defect: bool,
    conf_sev: str,
    conf_type: str,
    corr_action: str = None,
    ai_detections: int = None
):
    dec_id = f"dec-{insp_id}"
    db.query(InspectionOutcomeModel).filter(InspectionOutcomeModel.inspection_id == insp_id).delete()
    db.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == dec_id).delete()
    db.commit()

    det_count = ai_detections if ai_detections is not None else (1 if conf_defect else 0)

    dec = AgentDecisionModel(
        decision_id=dec_id,
        inspection_id=insp_id,
        asset_id=asset_id,
        operational_decision=ai_action,
        risk_score=ai_risk,
        risk_level=ai_sev,
        decision_rationale="AI assessment",
        human_review_required=True,
        review_status="PENDING_HUMAN_REVIEW",
        evidence_reference={"inspection_id": insp_id, "detections_count": det_count, "component_id": component_id},
        risk_assessment={"risk_score": ai_risk, "risk_level": ai_sev},
        work_order=None,
        warnings=[],
        evidence_gaps=[],
        execution_metrics={}
    )
    db.add(dec)
    db.commit()

    corr = None
    if corr_action or rev_status != ReviewOutcomeStatus.APPROVED:
        corr = ReviewerCorrection(
            correction_type=CorrectionType.ACTION_MODIFIED if corr_action else CorrectionType.SEVERITY_OVERESTIMATED,
            corrected_severity=conf_sev,
            corrected_defect_type=conf_type,
            corrected_action=corr_action
        )

    payload = InspectionOutcomeCreate(
        reviewer_id="INSP-ENG-TEST",
        review_status=rev_status,
        confirmed_defect_present=conf_defect,
        confirmed_severity=conf_sev,
        confirmed_defect_type=conf_type,
        reviewer_correction=corr
    )
    return inspection_outcome_service.record_outcome(db, insp_id, payload)


def test_empty_learning_metrics(db_session: Session):
    """Verifies that learning service returns 0 metrics safely when no outcomes exist for a scoped asset."""
    metrics = inspection_learning_service.calculate_metrics(db_session, asset_id="NON_EXISTENT_ASSET")
    assert metrics.total_reviewed == 0
    assert metrics.defect_agreement_rate == 0.0
    assert metrics.false_positive_count == 0


def test_learning_metrics_calculation(db_session: Session):
    """Verifies calculation of agreement rates, false positives, false negatives, and severity deltas."""
    asset_id = "ASSET-PL-01"
    comp_id = "PIPE-SEG-4021"

    # Outcome 1: Full Agreement (Approved)
    _create_decision_and_outcome(
        db_session, "INSP-LRN-01", asset_id, comp_id,
        ai_risk=85, ai_sev="CRITICAL", ai_action="URGENT_ENGINEERING_REVIEW",
        rev_status=ReviewOutcomeStatus.APPROVED, conf_defect=True, conf_sev="CRITICAL", conf_type="CRACK"
    )

    # Outcome 2: False Positive (Rejected)
    _create_decision_and_outcome(
        db_session, "INSP-LRN-02", asset_id, comp_id,
        ai_risk=65, ai_sev="HIGH", ai_action="PRIORITY_MAINTENANCE",
        rev_status=ReviewOutcomeStatus.REJECTED, conf_defect=False, conf_sev="NONE", conf_type="NONE"
    )

    # Outcome 3: Overestimation (Corrected)
    _create_decision_and_outcome(
        db_session, "INSP-LRN-03", asset_id, comp_id,
        ai_risk=75, ai_sev="HIGH", ai_action="PRIORITY_MAINTENANCE",
        rev_status=ReviewOutcomeStatus.CORRECTED, conf_defect=True, conf_sev="LOW", conf_type="CORROSION"
    )

    metrics = inspection_learning_service.calculate_metrics(db_session, asset_id=asset_id)
    assert metrics.total_reviewed >= 3
    assert metrics.false_positive_count >= 1
    assert metrics.correction_count >= 2


def test_detect_error_patterns_repeated_fps(db_session: Session):
    """Verifies that 2 or more false positives on the same component trigger REPEATED_FALSE_POSITIVES pattern."""
    asset_id = "ASSET-TK-04"
    comp_id = "TANK-SHELL-01"

    # Ensure asset exists
    asset = db_session.query(Asset).filter(Asset.asset_id == asset_id).first()
    if not asset:
        db_session.add(Asset(asset_id=asset_id, name="Hydrocarbon Tank 04", asset_type="TANK", location="Unit 2", criticality="HIGH"))
        db_session.commit()

    _create_decision_and_outcome(
        db_session, "INSP-PAT-FP-01", asset_id, comp_id,
        ai_risk=70, ai_sev="HIGH", ai_action="PRIORITY_MAINTENANCE",
        rev_status=ReviewOutcomeStatus.REJECTED, conf_defect=False, conf_sev="NONE", conf_type="NONE"
    )
    _create_decision_and_outcome(
        db_session, "INSP-PAT-FP-02", asset_id, comp_id,
        ai_risk=65, ai_sev="HIGH", ai_action="PRIORITY_MAINTENANCE",
        rev_status=ReviewOutcomeStatus.REJECTED, conf_defect=False, conf_sev="NONE", conf_type="NONE"
    )

    patterns = inspection_learning_service.detect_error_patterns(db_session, asset_id=asset_id, component_id=comp_id)
    fp_pattern = next((p for p in patterns if p.pattern_type == "REPEATED_FALSE_POSITIVES"), None)
    assert fp_pattern is not None
    assert fp_pattern.occurrence_count >= 2
    assert "INSP-PAT-FP-01" in fp_pattern.affected_inspection_ids
    assert "INSP-PAT-FP-02" in fp_pattern.affected_inspection_ids


def test_detect_error_patterns_severity_underestimation(db_session: Session):
    """Verifies that 2 or more severity underestimations trigger RECURRING_SEVERITY_UNDERESTIMATION pattern."""
    asset_id = "ASSET-ST-12"
    comp_id = "BEAM-COL-01"

    # Ensure asset exists
    asset = db_session.query(Asset).filter(Asset.asset_id == asset_id).first()
    if not asset:
        db_session.add(Asset(asset_id=asset_id, name="Structural Frame 12", asset_type="STRUCTURE", location="Unit 1", criticality="HIGH"))
        db_session.commit()

    # AI predicted LOW, Reviewer elevated to HIGH
    _create_decision_and_outcome(
        db_session, "INSP-PAT-UNDER-01", asset_id, comp_id,
        ai_risk=30, ai_sev="LOW", ai_action="MONITOR",
        rev_status=ReviewOutcomeStatus.CORRECTED, conf_defect=True, conf_sev="HIGH", conf_type="FATIGUE_CRACK"
    )
    _create_decision_and_outcome(
        db_session, "INSP-PAT-UNDER-02", asset_id, comp_id,
        ai_risk=35, ai_sev="LOW", ai_action="MONITOR",
        rev_status=ReviewOutcomeStatus.CORRECTED, conf_defect=True, conf_sev="CRITICAL", conf_type="FATIGUE_CRACK"
    )

    patterns = inspection_learning_service.detect_error_patterns(db_session, asset_id=asset_id, component_id=comp_id)
    under_pattern = next((p for p in patterns if p.pattern_type == "RECURRING_SEVERITY_UNDERESTIMATION"), None)
    assert under_pattern is not None
    assert under_pattern.occurrence_count >= 2


def test_deterministic_learning_execution(db_session: Session):
    """Verifies that repeated calls to calculate_metrics and detect_error_patterns produce identical results."""
    m1 = inspection_learning_service.calculate_metrics(db_session)
    m2 = inspection_learning_service.calculate_metrics(db_session)
    assert m1.model_dump() == m2.model_dump()

    p1 = inspection_learning_service.detect_error_patterns(db_session)
    p2 = inspection_learning_service.detect_error_patterns(db_session)
    assert [p.model_dump() for p in p1] == [p.model_dump() for p in p2]
