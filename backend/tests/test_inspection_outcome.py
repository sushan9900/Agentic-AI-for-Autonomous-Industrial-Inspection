"""Tests for Human Review Outcome Memory and Persistence (Phase 7A/7B)."""

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
from backend.app.services.inspection_outcome import (
    DuplicateOutcomeError,
    InspectionNotFoundError,
    OutcomeNotFoundError,
    inspection_outcome_service,
)


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
    risk_level: str = "CRITICAL",
    operational_decision: str = "URGENT_ENGINEERING_REVIEW"
) -> AgentDecisionModel:
    dec_id = f"dec-{inspection_id}"
    db.query(InspectionOutcomeModel).filter(InspectionOutcomeModel.inspection_id == inspection_id).delete()
    db.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == dec_id).delete()
    db.commit()

    decision = AgentDecisionModel(
        decision_id=dec_id,
        inspection_id=inspection_id,
        asset_id=asset_id,
        operational_decision=operational_decision,
        risk_score=risk_score,
        risk_level=risk_level,
        decision_rationale=f"Automated risk evaluation for {inspection_id}",
        human_review_required=True,
        review_status="PENDING_HUMAN_REVIEW",
        evidence_reference={"inspection_id": inspection_id, "detections_count": 1, "component_id": "PIPE-SEG-4021"},
        risk_assessment={"risk_score": risk_score, "risk_level": risk_level},
        work_order={"recommended_action": "NDE Ultrasonic Scan"},
        warnings=[],
        evidence_gaps=[],
        execution_metrics={}
    )
    db.add(decision)
    db.commit()
    return decision


def test_record_approved_outcome(db_session: Session):
    """Verifies recording an approved outcome where AI matched ground truth."""
    insp_id = "INSP-OUT-APP-01"
    _create_test_decision(db_session, insp_id, risk_score=85, risk_level="CRITICAL")

    payload = InspectionOutcomeCreate(
        reviewer_id="INSP-ENG-4401",
        review_status=ReviewOutcomeStatus.APPROVED,
        confirmed_defect_present=True,
        confirmed_severity="CRITICAL",
        confirmed_defect_type="CRACK",
        reviewer_comment="Physical crack verified on pipe segment 4021. AI risk and severity accepted.",
        confirmation_source=ConfirmationSource.VISUAL_INSPECTION,
        evidence_quality=EvidenceQuality.EXCELLENT
    )

    response = inspection_outcome_service.record_outcome(db_session, insp_id, payload)

    assert response.inspection_id == insp_id
    assert response.review_status == ReviewOutcomeStatus.APPROVED
    assert response.is_agreement is True
    assert response.ai_prediction.ai_risk_score == 85
    assert response.ai_prediction.ai_severity == "CRITICAL"
    assert response.confirmed_outcome.confirmed_severity == "CRITICAL"

    # Verify decision review_status updated to APPROVED
    dec = db_session.query(AgentDecisionModel).filter(AgentDecisionModel.inspection_id == insp_id).first()
    assert dec.review_status == "APPROVED"
    assert dec.reviewer_name == "INSP-ENG-4401"


def test_record_corrected_outcome(db_session: Session):
    """Verifies recording a corrected outcome where reviewer adjusts severity."""
    insp_id = "INSP-OUT-CORR-01"
    _create_test_decision(db_session, insp_id, risk_score=75, risk_level="HIGH")

    correction = ReviewerCorrection(
        correction_type=CorrectionType.SEVERITY_OVERESTIMATED,
        corrected_severity="MEDIUM",
        corrected_defect_type="SURFACE_CORROSION",
        corrected_action="MONITOR",
        justification="Corrosion depth is under 10% wall loss; downgraded from HIGH to MEDIUM."
    )

    payload = InspectionOutcomeCreate(
        reviewer_id="INSP-ENG-4402",
        review_status=ReviewOutcomeStatus.CORRECTED,
        confirmed_defect_present=True,
        confirmed_severity="MEDIUM",
        confirmed_defect_type="SURFACE_CORROSION",
        reviewer_correction=correction,
        reviewer_comment="Surface corrosion only; no structural crack.",
        confirmation_source=ConfirmationSource.FIELD_MEASUREMENT,
        evidence_quality=EvidenceQuality.ADEQUATE
    )

    response = inspection_outcome_service.record_outcome(db_session, insp_id, payload)

    assert response.review_status == ReviewOutcomeStatus.CORRECTED
    assert response.is_agreement is False
    assert response.confirmed_outcome.reviewer_correction is not None
    assert response.confirmed_outcome.reviewer_correction.corrected_severity == "MEDIUM"

    dec = db_session.query(AgentDecisionModel).filter(AgentDecisionModel.inspection_id == insp_id).first()
    assert dec.review_status == "CORRECTED"


def test_record_rejected_outcome(db_session: Session):
    """Verifies recording a rejected outcome where reviewer confirms defect is absent (false positive)."""
    insp_id = "INSP-OUT-REJ-01"
    _create_test_decision(db_session, insp_id, risk_score=65, risk_level="HIGH")

    correction = ReviewerCorrection(
        correction_type=CorrectionType.DEFECT_ABSENT,
        corrected_severity="NONE",
        corrected_defect_type="NONE",
        corrected_action="NO_ACTION",
        justification="Artifact was shadow glare on weld cap; no crack."
    )

    payload = InspectionOutcomeCreate(
        reviewer_id="INSP-ENG-4403",
        review_status=ReviewOutcomeStatus.REJECTED,
        confirmed_defect_present=False,
        confirmed_severity="NONE",
        confirmed_defect_type="NONE",
        reviewer_correction=correction,
        reviewer_comment="False positive caused by lighting artifact."
    )

    response = inspection_outcome_service.record_outcome(db_session, insp_id, payload)
    assert response.review_status == ReviewOutcomeStatus.REJECTED
    assert response.is_agreement is False
    assert response.confirmed_outcome.confirmed_defect_present is False


def test_duplicate_outcome_rejected(db_session: Session):
    """Verifies that submitting a second outcome for the same inspection and reviewer raises DuplicateOutcomeError."""
    insp_id = "INSP-OUT-DUP-01"
    _create_test_decision(db_session, insp_id)

    payload = InspectionOutcomeCreate(
        reviewer_id="INSP-ENG-DUP",
        review_status=ReviewOutcomeStatus.APPROVED,
        confirmed_defect_present=True,
        confirmed_severity="HIGH",
        confirmed_defect_type="CRACK"
    )
    inspection_outcome_service.record_outcome(db_session, insp_id, payload)

    with pytest.raises(DuplicateOutcomeError):
        inspection_outcome_service.record_outcome(db_session, insp_id, payload)


def test_missing_inspection_raises_error(db_session: Session):
    """Verifies that attempting to record an outcome for non-existent inspection raises InspectionNotFoundError."""
    payload = InspectionOutcomeCreate(
        reviewer_id="INSP-ENG-999",
        review_status=ReviewOutcomeStatus.APPROVED,
        confirmed_defect_present=True,
        confirmed_severity="HIGH",
        confirmed_defect_type="CRACK"
    )
    with pytest.raises(InspectionNotFoundError):
        inspection_outcome_service.record_outcome(db_session, "NON_EXISTENT_INSP_ID", payload)


def test_get_and_list_outcomes(db_session: Session):
    """Verifies retrieving by inspection_id and listing outcomes with filters."""
    insp_id = "INSP-OUT-LIST-01"
    _create_test_decision(db_session, insp_id)

    payload = InspectionOutcomeCreate(
        reviewer_id="INSP-ENG-LIST",
        review_status=ReviewOutcomeStatus.APPROVED,
        confirmed_defect_present=True,
        confirmed_severity="HIGH",
        confirmed_defect_type="CRACK"
    )
    inspection_outcome_service.record_outcome(db_session, insp_id, payload)

    fetched = inspection_outcome_service.get_outcome(db_session, insp_id)
    assert fetched.inspection_id == insp_id

    listing = inspection_outcome_service.list_outcomes(db_session, asset_id="ASSET-PL-01", limit=10)
    assert listing.total >= 1
    assert any(item.inspection_id == insp_id for item in listing.items)
