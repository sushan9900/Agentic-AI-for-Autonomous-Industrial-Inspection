"""Inspection Orchestration State Machine Service (Phase 8B)."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.database.models.inspection_task import (
    InspectionTaskModel,
    InspectionTaskTransitionModel,
)
from backend.app.schemas.inspection_task import (
    ActorType,
    InspectionTaskResponse,
    InspectionTaskTransitionRequest,
    TaskState,
)
from backend.app.schemas.orchestration import (
    OrchestrationAuditEvent,
    OrchestrationAuditResponse,
    StateTransitionValidation,
)
from backend.app.services.inspection_task import (
    TaskNotFoundError,
    inspection_task_service,
)


class InvalidStateTransitionError(Exception):
    """Raised when an illegal transition is attempted according to state machine matrix."""
    pass


class UnauthorizedTransitionError(Exception):
    """Raised when an actor lacks the necessary authority to execute a specific transition."""
    pass


class InspectionOrchestrator:
    """
    Deterministic finite state machine managing all operational inspection task transitions.
    Validates current state, requested state, actor authority, and human review requirements.
    No LLM is used to decide transitions.
    """

    VALID_TRANSITIONS: Dict[TaskState, Set[TaskState]] = {
        TaskState.CREATED: {TaskState.QUEUED, TaskState.CANCELLED, TaskState.REJECTED},
        TaskState.QUEUED: {TaskState.ASSIGNED_FOR_REVIEW, TaskState.IN_REVIEW, TaskState.CANCELLED},
        TaskState.ASSIGNED_FOR_REVIEW: {TaskState.IN_REVIEW, TaskState.QUEUED, TaskState.CANCELLED},
        TaskState.IN_REVIEW: {TaskState.AWAITING_EVIDENCE, TaskState.REVIEWED, TaskState.REJECTED, TaskState.CANCELLED},
        TaskState.AWAITING_EVIDENCE: {TaskState.IN_REVIEW, TaskState.CANCELLED},
        TaskState.REVIEWED: {TaskState.COMPLETED, TaskState.IN_REVIEW, TaskState.REJECTED},
        TaskState.COMPLETED: set(),
        TaskState.CANCELLED: set(),
        TaskState.REJECTED: set(),
    }

    def validate_transition(
        self,
        current_state: TaskState,
        requested_state: TaskState,
        actor_type: ActorType
    ) -> StateTransitionValidation:
        """Determines whether a prospective state transition is valid under the state machine rules."""
        # 1. Check state graph connectivity
        allowed_targets = self.VALID_TRANSITIONS.get(current_state, set())
        if requested_state not in allowed_targets:
            return StateTransitionValidation(
                is_valid=False,
                current_state=current_state,
                requested_state=requested_state,
                actor_type=actor_type,
                allowed=False,
                rejection_reason=(
                    f"Illegal transition: Cannot transition from '{current_state.value}' "
                    f"to '{requested_state.value}'."
                )
            )

        # 2. Strict Safety Gate: Only HUMAN_REVIEWER may finalize tasks into COMPLETED
        if requested_state == TaskState.COMPLETED and actor_type != ActorType.HUMAN_REVIEWER:
            return StateTransitionValidation(
                is_valid=False,
                current_state=current_state,
                requested_state=requested_state,
                actor_type=actor_type,
                allowed=False,
                rejection_reason=(
                    f"Safety Violation: Actor '{actor_type.value}' cannot transition task to COMPLETED. "
                    "Only an authorized HUMAN_REVIEWER may finalize an inspection task."
                )
            )

        # 3. Actor authority: SYSTEM_RECOMMENDATION cannot reject tasks directly
        if requested_state == TaskState.REJECTED and actor_type == ActorType.SYSTEM_RECOMMENDATION:
            return StateTransitionValidation(
                is_valid=False,
                current_state=current_state,
                requested_state=requested_state,
                actor_type=actor_type,
                allowed=False,
                rejection_reason="SYSTEM_RECOMMENDATION cannot reject tasks; rejection requires human authorization."
            )

        return StateTransitionValidation(
            is_valid=True,
            current_state=current_state,
            requested_state=requested_state,
            actor_type=actor_type,
            allowed=True,
            rejection_reason=None
        )

    def transition_task(
        self,
        db: Session,
        task_id: str,
        request: InspectionTaskTransitionRequest
    ) -> InspectionTaskResponse:
        """
        Executes an authorized state transition for an inspection task.
        Validates transition legality, updates task state, and logs immutable audit ledger record.
        """
        task = db.query(InspectionTaskModel).filter(InspectionTaskModel.task_id == task_id).first()
        if not task:
            raise TaskNotFoundError(f"Inspection task '{task_id}' was not found.")

        current_state = TaskState(task.state)
        validation = self.validate_transition(
            current_state=current_state,
            requested_state=request.new_state,
            actor_type=request.actor_type
        )

        if not validation.is_valid:
            if "Safety Violation" in (validation.rejection_reason or ""):
                raise UnauthorizedTransitionError(validation.rejection_reason)
            raise InvalidStateTransitionError(validation.rejection_reason)

        now = datetime.now(timezone.utc)

        # 1. Update task state
        task.state = request.new_state.value
        task.updated_at = now

        # 2. Record immutable transition entry
        transition_id = f"tr-{uuid.uuid4().hex[:12]}"
        transition_record = InspectionTaskTransitionModel(
            transition_id=transition_id,
            task_id=task.task_id,
            inspection_id=task.inspection_id,
            previous_state=current_state.value,
            new_state=request.new_state.value,
            actor_type=request.actor_type.value,
            actor_id=request.actor_id,
            reason=request.reason,
            transition_metadata=request.transition_metadata or {},
            created_at=now
        )
        db.add(transition_record)
        db.commit()
        db.refresh(task)

        return inspection_task_service.get_task(db=db, task_id=task_id)

    def get_audit_trail(
        self,
        db: Session,
        task_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> OrchestrationAuditResponse:
        """Retrieves paginated historical state transition audit records."""
        query = db.query(InspectionTaskTransitionModel)
        if task_id:
            query = query.filter(InspectionTaskTransitionModel.task_id == task_id)

        total = query.count()
        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, offset)

        records = (
            query.order_by(desc(InspectionTaskTransitionModel.created_at))
            .offset(safe_offset)
            .limit(safe_limit)
            .all()
        )

        events = [
            OrchestrationAuditEvent(
                event_id=r.transition_id,
                task_id=r.task_id,
                inspection_id=r.inspection_id,
                previous_state=TaskState(r.previous_state) if r.previous_state in TaskState.__members__ else TaskState.CREATED,
                new_state=TaskState(r.new_state),
                actor_type=ActorType(r.actor_type),
                actor_id=r.actor_id,
                reason=r.reason,
                metadata=r.transition_metadata or {},
                timestamp=r.created_at
            )
            for r in records
        ]

        return OrchestrationAuditResponse(total_events=total, events=events)


inspection_orchestrator = InspectionOrchestrator()
