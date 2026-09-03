"""Tests for Inspection Task Lifecycle and Service (Phase 8A)."""

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models.asset import Asset
from backend.app.database.models.inspection_task import (
    InspectionTaskModel,
    InspectionTaskTransitionModel,
)
from backend.app.database.session import SessionLocal
from backend.app.schemas.inspection_task import (
    ActorType,
    InspectionTaskCreate,
    TaskPriority,
    TaskState,
    TaskType,
    TimingWindow,
)
from backend.app.services.inspection_task import (
    AssetNotFoundError,
    TaskNotFoundError,
    inspection_task_service,
)


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    # Ensure test asset exists
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


def test_create_inspection_task(db_session: Session):
    """Verifies creating an inspection task in CREATED state with audit transition."""
    payload = InspectionTaskCreate(
        inspection_id="INSP-TASK-TEST-01",
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        task_type=TaskType.VISUAL_INSPECTION,
        priority=TaskPriority.HIGH,
        timing_window=TimingWindow.WITHIN_24_HOURS,
        assigned_to="ENG-INSP-101",
        payload={"notes": "Verify weld seam after ultrasonic alert"}
    )

    task = inspection_task_service.create_task(
        db=db_session,
        payload=payload,
        actor_type=ActorType.SYSTEM_RECOMMENDATION,
        reason="Scheduled diagnostic verification"
    )

    assert task.task_id.startswith("task-")
    assert task.state == TaskState.CREATED
    assert task.priority == TaskPriority.HIGH
    assert task.timing_window == TimingWindow.WITHIN_24_HOURS
    assert len(task.transitions) == 1
    assert task.transitions[0].new_state == TaskState.CREATED
    assert task.transitions[0].actor_type == ActorType.SYSTEM_RECOMMENDATION


def test_get_task_not_found(db_session: Session):
    """Verifies that requesting non-existent task raises TaskNotFoundError."""
    with pytest.raises(TaskNotFoundError):
        inspection_task_service.get_task(db_session, "task-non-existent-99999")


def test_create_task_invalid_asset(db_session: Session):
    """Verifies that creating task for non-existent asset raises AssetNotFoundError."""
    payload = InspectionTaskCreate(
        asset_id="NON-EXISTENT-ASSET-000",
        task_type=TaskType.VISUAL_INSPECTION
    )
    with pytest.raises(AssetNotFoundError):
        inspection_task_service.create_task(db_session, payload)


def test_list_tasks_and_filter(db_session: Session):
    """Verifies listing tasks with filtering by state and asset."""
    payload = InspectionTaskCreate(
        asset_id="ASSET-PL-01",
        component_id="PIPE-VALVE-01",
        task_type=TaskType.SUPPLEMENTAL_NDE,
        priority=TaskPriority.CRITICAL,
        timing_window=TimingWindow.IMMEDIATE
    )
    created = inspection_task_service.create_task(db_session, payload)

    results = inspection_task_service.list_tasks(
        db=db_session,
        asset_id="ASSET-PL-01",
        state="CREATED",
        limit=10
    )
    assert results.total >= 1
    assert any(t.task_id == created.task_id for t in results.items)


def test_task_transitions_retrieval(db_session: Session):
    """Verifies retrieving historical transition records for a task."""
    payload = InspectionTaskCreate(
        asset_id="ASSET-PL-01",
        task_type=TaskType.EXPERT_EVALUATION
    )
    created = inspection_task_service.create_task(db_session, payload)

    transitions = inspection_task_service.get_task_transitions(db_session, created.task_id)
    assert len(transitions) == 1
    assert transitions[0].task_id == created.task_id
    assert transitions[0].new_state == TaskState.CREATED
