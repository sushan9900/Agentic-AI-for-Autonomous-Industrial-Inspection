"""Inspection Task Lifecycle Service (Phase 8A)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.database.models.asset import Asset
from backend.app.database.models.inspection_task import (
    InspectionTaskModel,
    InspectionTaskTransitionModel,
)
from backend.app.schemas.inspection_task import (
    ActorType,
    InspectionTaskCreate,
    InspectionTaskListResponse,
    InspectionTaskResponse,
    InspectionTaskTransitionResponse,
    TaskPriority,
    TaskState,
    TaskType,
    TimingWindow,
)


class TaskNotFoundError(Exception):
    """Raised when the referenced inspection task does not exist."""
    pass


class AssetNotFoundError(Exception):
    """Raised when the referenced target asset does not exist."""
    pass


class InspectionTaskService:
    """
    Service managing inspection tasks and persistent state transitions.
    Enforces auditable task lifecycles without executing maintenance or plant control.
    """

    def create_task(
        self,
        db: Session,
        payload: InspectionTaskCreate,
        actor_type: ActorType = ActorType.SYSTEM_RECOMMENDATION,
        actor_id: Optional[str] = None,
        reason: str = "Initial task instantiation"
    ) -> InspectionTaskResponse:
        """Creates a new inspection task in CREATED state with audit transition record."""
        # 1. Verify asset exists
        asset = db.query(Asset).filter(Asset.asset_id == payload.asset_id).first()
        if not asset:
            raise AssetNotFoundError(f"Asset '{payload.asset_id}' was not found in asset registry.")

        now = datetime.now(timezone.utc)
        task_id = f"task-{uuid.uuid4().hex[:12]}"

        # 2. Persist task record
        task_record = InspectionTaskModel(
            task_id=task_id,
            inspection_id=payload.inspection_id,
            asset_id=payload.asset_id,
            component_id=payload.component_id,
            state=TaskState.CREATED.value,
            task_type=payload.task_type.value,
            priority=payload.priority.value,
            timing_window=payload.timing_window.value,
            assigned_to=payload.assigned_to,
            payload=payload.payload or {},
            created_at=now,
            updated_at=now
        )
        db.add(task_record)

        # 3. Create initial transition record
        transition_id = f"tr-{uuid.uuid4().hex[:12]}"
        transition_record = InspectionTaskTransitionModel(
            transition_id=transition_id,
            task_id=task_id,
            inspection_id=payload.inspection_id,
            previous_state="NONE",
            new_state=TaskState.CREATED.value,
            actor_type=actor_type.value,
            actor_id=actor_id,
            reason=reason,
            transition_metadata={"initial_priority": payload.priority.value, "timing_window": payload.timing_window.value},
            created_at=now
        )
        db.add(transition_record)

        db.commit()
        db.refresh(task_record)

        return self._to_response(task_record, [transition_record])

    def get_task(self, db: Session, task_id: str) -> InspectionTaskResponse:
        """Retrieves an inspection task by its unique ID with full transition history."""
        task = db.query(InspectionTaskModel).filter(InspectionTaskModel.task_id == task_id).first()
        if not task:
            raise TaskNotFoundError(f"Inspection task with ID '{task_id}' was not found.")

        transitions = (
            db.query(InspectionTaskTransitionModel)
            .filter(InspectionTaskTransitionModel.task_id == task_id)
            .order_by(InspectionTaskTransitionModel.created_at.asc())
            .all()
        )
        return self._to_response(task, transitions)

    def list_tasks(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None,
        state: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> InspectionTaskListResponse:
        """Retrieves paginated inspection tasks with optional filters."""
        query = db.query(InspectionTaskModel)

        if asset_id:
            query = query.filter(InspectionTaskModel.asset_id == asset_id)
        if component_id:
            query = query.filter(InspectionTaskModel.component_id == component_id)
        if state:
            query = query.filter(InspectionTaskModel.state == state.upper().strip())
        if priority:
            query = query.filter(InspectionTaskModel.priority == priority.upper().strip())

        total = query.count()
        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, offset)

        tasks = (
            query.order_by(desc(InspectionTaskModel.created_at))
            .offset(safe_offset)
            .limit(safe_limit)
            .all()
        )

        # Batch load transitions to prevent N+1 queries
        task_ids = [t.task_id for t in tasks]
        transitions_by_task = {}
        if task_ids:
            all_transitions = (
                db.query(InspectionTaskTransitionModel)
                .filter(InspectionTaskTransitionModel.task_id.in_(task_ids))
                .order_by(InspectionTaskTransitionModel.created_at.asc())
                .all()
            )
            for tr in all_transitions:
                transitions_by_task.setdefault(tr.task_id, []).append(tr)

        items = [self._to_response(t, transitions_by_task.get(t.task_id, [])) for t in tasks]

        return InspectionTaskListResponse(total=total, items=items)

    def get_task_transitions(self, db: Session, task_id: str) -> List[InspectionTaskTransitionResponse]:
        """Retrieves all historical transition records for a task."""
        records = (
            db.query(InspectionTaskTransitionModel)
            .filter(InspectionTaskTransitionModel.task_id == task_id)
            .order_by(InspectionTaskTransitionModel.created_at.asc())
            .all()
        )
        return [self._to_transition_response(r) for r in records]

    def _to_response(
        self,
        task: InspectionTaskModel,
        transitions: List[InspectionTaskTransitionModel]
    ) -> InspectionTaskResponse:
        """Converts an ORM task model into a Pydantic response."""
        return InspectionTaskResponse(
            id=task.id,
            task_id=task.task_id,
            inspection_id=task.inspection_id,
            asset_id=task.asset_id,
            component_id=task.component_id,
            state=TaskState(task.state),
            task_type=TaskType(task.task_type),
            priority=TaskPriority(task.priority),
            timing_window=TimingWindow(task.timing_window),
            assigned_to=task.assigned_to,
            payload=task.payload or {},
            created_at=task.created_at,
            updated_at=task.updated_at,
            transitions=[self._to_transition_response(tr) for tr in transitions]
        )

    def _to_transition_response(self, record: InspectionTaskTransitionModel) -> InspectionTaskTransitionResponse:
        """Converts an ORM transition model into a Pydantic response."""
        prev_state = TaskState(record.previous_state) if record.previous_state in TaskState.__members__ else TaskState.CREATED
        return InspectionTaskTransitionResponse(
            id=record.id,
            transition_id=record.transition_id,
            task_id=record.task_id,
            inspection_id=record.inspection_id,
            previous_state=prev_state,
            new_state=TaskState(record.new_state),
            actor_type=ActorType(record.actor_type),
            actor_id=record.actor_id,
            reason=record.reason,
            transition_metadata=record.transition_metadata or {},
            created_at=record.created_at
        )


inspection_task_service = InspectionTaskService()
