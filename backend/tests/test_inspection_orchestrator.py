"""Tests for Inspection Orchestration State Machine (Phase 8B)."""

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models.asset import Asset
from backend.app.database.session import SessionLocal
from backend.app.schemas.inspection_task import (
    ActorType,
    InspectionTaskCreate,
    InspectionTaskTransitionRequest,
    TaskPriority,
    TaskState,
    TaskType,
    TimingWindow,
)
from backend.app.services.inspection_orchestrator import (
    InvalidStateTransitionError,
    UnauthorizedTransitionError,
    inspection_orchestrator,
)
from backend.app.services.inspection_task import inspection_task_service


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


def _create_fresh_task(db: Session) -> str:
    payload = InspectionTaskCreate(
        asset_id="ASSET-PL-01",
        task_type=TaskType.VISUAL_INSPECTION,
        priority=TaskPriority.HIGH,
        timing_window=TimingWindow.WITHIN_24_HOURS
    )
    task = inspection_task_service.create_task(db, payload)
    return task.task_id


def test_valid_task_progression(db_session: Session):
    """Verifies full valid progression from CREATED through COMPLETED by authorized human."""
    task_id = _create_fresh_task(db_session)

    # 1. CREATED -> QUEUED
    t1 = inspection_orchestrator.transition_task(
        db_session,
        task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.QUEUED,
            actor_type=ActorType.SYSTEM_RECOMMENDATION,
            reason="Queued for inspection review"
        )
    )
    assert t1.state == TaskState.QUEUED

    # 2. QUEUED -> IN_REVIEW
    t2 = inspection_orchestrator.transition_task(
        db_session,
        task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.IN_REVIEW,
            actor_type=ActorType.HUMAN_REVIEWER,
            actor_id="ENG-402",
            reason="Inspector started active examination"
        )
    )
    assert t2.state == TaskState.IN_REVIEW

    # 3. IN_REVIEW -> REVIEWED
    t3 = inspection_orchestrator.transition_task(
        db_session,
        task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.REVIEWED,
            actor_type=ActorType.HUMAN_REVIEWER,
            actor_id="ENG-402",
            reason="Diagnostic review completed"
        )
    )
    assert t3.state == TaskState.REVIEWED

    # 4. REVIEWED -> COMPLETED (Authorized by Human Reviewer)
    t4 = inspection_orchestrator.transition_task(
        db_session,
        task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.COMPLETED,
            actor_type=ActorType.HUMAN_REVIEWER,
            actor_id="CHIEF-ENG-901",
            reason="Final signoff by chief engineer"
        )
    )
    assert t4.state == TaskState.COMPLETED
    assert len(t4.transitions) == 5  # CREATED + 4 transitions


def test_system_cannot_complete_task(db_session: Session):
    """
    CRITICAL INVARIANT: SYSTEM_RECOMMENDATION cannot transition task to COMPLETED.
    Must raise UnauthorizedTransitionError.
    """
    task_id = _create_fresh_task(db_session)

    # Fast forward to REVIEWED
    inspection_orchestrator.transition_task(
        db_session, task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.QUEUED, actor_type=ActorType.SYSTEM_RECOMMENDATION, reason="Queued"
        )
    )
    inspection_orchestrator.transition_task(
        db_session, task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.IN_REVIEW, actor_type=ActorType.HUMAN_REVIEWER, actor_id="ENG-1", reason="Examining"
        )
    )
    inspection_orchestrator.transition_task(
        db_session, task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.REVIEWED, actor_type=ActorType.HUMAN_REVIEWER, actor_id="ENG-1", reason="Reviewed"
        )
    )

    # Attempt to finalize via SYSTEM_RECOMMENDATION must fail
    with pytest.raises(UnauthorizedTransitionError) as exc:
        inspection_orchestrator.transition_task(
            db_session, task_id,
            InspectionTaskTransitionRequest(
                new_state=TaskState.COMPLETED,
                actor_type=ActorType.SYSTEM_RECOMMENDATION,
                reason="Autonomous finalization attempt"
            )
        )
    assert "Safety Violation" in str(exc.value)


def test_illegal_transition_rejected(db_session: Session):
    """Verifies that jumping states illegally (e.g. CREATED -> COMPLETED) is rejected."""
    task_id = _create_fresh_task(db_session)

    with pytest.raises(InvalidStateTransitionError):
        inspection_orchestrator.transition_task(
            db_session, task_id,
            InspectionTaskTransitionRequest(
                new_state=TaskState.COMPLETED,
                actor_type=ActorType.HUMAN_REVIEWER,
                reason="Attempted state jump"
            )
        )


def test_terminal_state_invariance(db_session: Session):
    """Verifies that once in terminal state (e.g. CANCELLED), further transitions are blocked."""
    task_id = _create_fresh_task(db_session)

    # Cancel task
    inspection_orchestrator.transition_task(
        db_session, task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.CANCELLED,
            actor_type=ActorType.HUMAN_REVIEWER,
            reason="Decommissioned inspection"
        )
    )

    # Attempt to reopen into IN_REVIEW
    with pytest.raises(InvalidStateTransitionError):
        inspection_orchestrator.transition_task(
            db_session, task_id,
            InspectionTaskTransitionRequest(
                new_state=TaskState.IN_REVIEW,
                actor_type=ActorType.HUMAN_REVIEWER,
                reason="Attempted reactivation"
            )
        )


def test_audit_trail_retrieval(db_session: Session):
    """Verifies retrieving audit trail events for a task."""
    task_id = _create_fresh_task(db_session)
    inspection_orchestrator.transition_task(
        db_session, task_id,
        InspectionTaskTransitionRequest(
            new_state=TaskState.QUEUED, actor_type=ActorType.SYSTEM_RECOMMENDATION, reason="Queued"
        )
    )

    audit = inspection_orchestrator.get_audit_trail(db_session, task_id=task_id)
    assert audit.total_events >= 2
    assert all(e.task_id == task_id for e in audit.events)
