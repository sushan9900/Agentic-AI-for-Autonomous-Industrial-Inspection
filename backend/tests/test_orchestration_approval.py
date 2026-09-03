"""Tests for Orchestration Human Approval Gate (Phase 8F)."""

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models.asset import Asset
from backend.app.database.session import SessionLocal
from backend.app.schemas.inspection_task import TaskPriority, TimingWindow
from backend.app.schemas.orchestration_approval import (
    ApprovalDecisionRequest,
    ApprovalStatus,
)
from backend.app.schemas.task_recommendation import (
    RecommendationType,
    RecommendationUrgency,
    TaskRecommendation,
)
from backend.app.services.inspection_task import inspection_task_service
from backend.app.services.orchestration_approval import (
    ApprovalAlreadyProcessedError,
    ApprovalNotFoundError,
    orchestration_approval_service,
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


def _mock_recommendation(rec_id: str) -> TaskRecommendation:
    import uuid
    unique_rec_id = f"{rec_id}-{uuid.uuid4().hex[:8]}"
    return TaskRecommendation(
        recommendation_id=unique_rec_id,
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        inspection_id="INSP-MOCK-01",
        recommendation_type=RecommendationType.REPEAT_INSPECTION,
        urgency=RecommendationUrgency.HIGH,
        timing_window=TimingWindow.WITHIN_24_HOURS,
        reason="Repeated defect detection warrants verification inspection.",
        supporting_evidence_ids=[],
        supporting_inspection_ids=["INSP-MOCK-01"],
        authoritative=False,
        human_approval_required=True
    )


def test_create_and_approve_recommendation(db_session: Session):
    """Verifies that approving a recommendation spawns an active inspection task."""
    rec = _mock_recommendation("rec-test-appr-01")
    orchestration_approval_service.create_pending_approval(db_session, rec)

    decision = ApprovalDecisionRequest(
        reviewer_id="CHIEF-ENG-101",
        status=ApprovalStatus.APPROVED,
        reviewer_comment="Authorized repeat inspection for tomorrow morning."
    )

    result = orchestration_approval_service.process_approval(db_session, rec.recommendation_id, decision)
    assert result.status == ApprovalStatus.APPROVED
    assert result.reviewer_id == "CHIEF-ENG-101"
    assert result.task_id is not None

    # Verify task was created in CREATED state
    task = inspection_task_service.get_task(db_session, result.task_id)
    assert task.asset_id == "ASSET-PL-01"
    assert task.priority == TaskPriority.HIGH


def test_modify_recommendation(db_session: Session):
    """Verifies that human modification overrides recommended parameters and preserves modifications."""
    rec = _mock_recommendation("rec-test-mod-01")
    orchestration_approval_service.create_pending_approval(db_session, rec)

    decision = ApprovalDecisionRequest(
        reviewer_id="CHIEF-ENG-102",
        status=ApprovalStatus.MODIFIED,
        reviewer_comment="Elevating urgency to CRITICAL and scheduling IMMEDIATE.",
        modifications={"priority": "CRITICAL", "timing_window": "IMMEDIATE"}
    )

    result = orchestration_approval_service.process_approval(db_session, rec.recommendation_id, decision)
    assert result.status == ApprovalStatus.MODIFIED
    assert result.modifications == {"priority": "CRITICAL", "timing_window": "IMMEDIATE"}
    assert result.task_id is not None

    task = inspection_task_service.get_task(db_session, result.task_id)
    assert task.priority == TaskPriority.CRITICAL
    assert task.timing_window == TimingWindow.IMMEDIATE


def test_reject_recommendation(db_session: Session):
    """Verifies that rejecting a recommendation does NOT spawn a task and preserves audit record."""
    rec = _mock_recommendation("rec-test-rej-01")
    orchestration_approval_service.create_pending_approval(db_session, rec)

    decision = ApprovalDecisionRequest(
        reviewer_id="CHIEF-ENG-103",
        status=ApprovalStatus.REJECTED,
        reviewer_comment="Disapproved: recent manual ultrasound showed no wall thinning."
    )

    result = orchestration_approval_service.process_approval(db_session, rec.recommendation_id, decision)
    assert result.status == ApprovalStatus.REJECTED
    assert result.task_id is None
    assert result.reviewer_comment == "Disapproved: recent manual ultrasound showed no wall thinning."


def test_reprocess_already_finalized_approval_fails(db_session: Session):
    """Verifies that attempting to re-process an already decided approval raises error."""
    rec = _mock_recommendation("rec-test-dup-01")
    orchestration_approval_service.create_pending_approval(db_session, rec)

    decision = ApprovalDecisionRequest(
        reviewer_id="CHIEF-ENG-104",
        status=ApprovalStatus.APPROVED
    )
    orchestration_approval_service.process_approval(db_session, rec.recommendation_id, decision)

    with pytest.raises(ApprovalAlreadyProcessedError):
        orchestration_approval_service.process_approval(db_session, rec.recommendation_id, decision)
