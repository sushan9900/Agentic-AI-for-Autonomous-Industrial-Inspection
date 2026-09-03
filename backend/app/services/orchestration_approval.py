"""Human Approval Gate Service for Orchestration Recommendations (Phase 8F)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.database.models.inspection_task import OrchestrationApprovalModel
from backend.app.schemas.inspection_task import (
    ActorType,
    InspectionTaskCreate,
    TaskPriority,
    TaskType,
    TimingWindow,
)
from backend.app.schemas.orchestration_approval import (
    ApprovalDecisionRequest,
    ApprovalStatus,
    OrchestrationApprovalListResponse,
    OrchestrationApprovalResponse,
)
from backend.app.schemas.task_recommendation import TaskRecommendation
from backend.app.services.inspection_task import inspection_task_service


class ApprovalNotFoundError(Exception):
    """Raised when the referenced recommendation approval record is not found."""
    pass


class ApprovalAlreadyProcessedError(Exception):
    """Raised when attempting to re-decide an already finalized approval."""
    pass


class OrchestrationApprovalService:
    """
    Human approval gate ensuring no AI orchestration recommendation executes
    without explicit human engineering authorization.
    """

    def create_pending_approval(
        self,
        db: Session,
        recommendation: TaskRecommendation
    ) -> OrchestrationApprovalResponse:
        """Instantiates a pending human approval gate entry for a generated recommendation."""
        existing = (
            db.query(OrchestrationApprovalModel)
            .filter(OrchestrationApprovalModel.recommendation_id == recommendation.recommendation_id)
            .first()
        )
        if existing:
            return self._to_response(existing)

        now = datetime.now(timezone.utc)
        approval_id = f"appr-{uuid.uuid4().hex[:12]}"

        record = OrchestrationApprovalModel(
            approval_id=approval_id,
            recommendation_id=recommendation.recommendation_id,
            task_id=None,
            status=ApprovalStatus.PENDING.value,
            reviewer_id=None,
            reviewer_comment=None,
            original_recommendation=recommendation.model_dump(mode="json"),
            modifications=None,
            reviewed_at=None,
            created_at=now
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return self._to_response(record)

    def process_approval(
        self,
        db: Session,
        recommendation_id: str,
        request: ApprovalDecisionRequest
    ) -> OrchestrationApprovalResponse:
        """
        Executes an authorized human approval decision (APPROVED, MODIFIED, or REJECTED).
        Spawns an active InspectionTaskModel only upon APPROVED or MODIFIED status.
        """
        record = (
            db.query(OrchestrationApprovalModel)
            .filter(OrchestrationApprovalModel.recommendation_id == recommendation_id)
            .first()
        )
        if not record:
            raise ApprovalNotFoundError(f"Approval record for recommendation '{recommendation_id}' was not found.")

        if record.status != ApprovalStatus.PENDING.value:
            raise ApprovalAlreadyProcessedError(
                f"Recommendation '{recommendation_id}' has already been processed with status '{record.status}'."
            )

        now = datetime.now(timezone.utc)
        orig = record.original_recommendation or {}

        # 1. Handle REJECTED
        if request.status == ApprovalStatus.REJECTED:
            record.status = ApprovalStatus.REJECTED.value
            record.reviewer_id = request.reviewer_id.strip()
            record.reviewer_comment = request.reviewer_comment
            record.reviewed_at = now
            db.commit()
            db.refresh(record)
            return self._to_response(record)

        # 2. Handle APPROVED or MODIFIED -> Instantiate InspectionTask
        task_type_str = orig.get("recommendation_type", "VISUAL_INSPECTION")
        # Map recommendation type to task type
        task_type = (
            TaskType.RE_INSPECTION if "REPEAT" in task_type_str
            else TaskType.EXPERT_EVALUATION if "EXPERT" in task_type_str
            else TaskType.EVIDENCE_COLLECTION if "EVIDENCE" in task_type_str
            else TaskType.VISUAL_INSPECTION
        )

        priority_str = orig.get("urgency", "MEDIUM")
        priority = TaskPriority(priority_str) if priority_str in TaskPriority.__members__ else TaskPriority.MEDIUM

        timing_str = orig.get("timing_window", "ROUTINE")
        timing = TimingWindow(timing_str) if timing_str in TimingWindow.__members__ else TimingWindow.ROUTINE

        # Apply human modifications if status is MODIFIED
        if request.status == ApprovalStatus.MODIFIED and request.modifications:
            record.modifications = request.modifications
            if "priority" in request.modifications:
                p_val = request.modifications["priority"]
                if p_val in TaskPriority.__members__:
                    priority = TaskPriority(p_val)
            if "timing_window" in request.modifications:
                t_val = request.modifications["timing_window"]
                if t_val in TimingWindow.__members__:
                    timing = TimingWindow(t_val)
            if "task_type" in request.modifications:
                tt_val = request.modifications["task_type"]
                if tt_val in TaskType.__members__:
                    task_type = TaskType(tt_val)

        task_payload = InspectionTaskCreate(
            inspection_id=orig.get("inspection_id"),
            asset_id=orig.get("asset_id", "UNKNOWN"),
            component_id=orig.get("component_id"),
            task_type=task_type,
            priority=priority,
            timing_window=timing,
            assigned_to=request.reviewer_id.strip(),
            payload={
                "source_recommendation_id": recommendation_id,
                "recommendation_reason": orig.get("reason"),
                "approval_comments": request.reviewer_comment
            }
        )

        created_task = inspection_task_service.create_task(
            db=db,
            payload=task_payload,
            actor_type=ActorType.HUMAN_REVIEWER,
            actor_id=request.reviewer_id.strip(),
            reason=f"Human approved recommendation: {request.reviewer_comment or 'Standard authorization'}"
        )

        record.status = request.status.value
        record.task_id = created_task.task_id
        record.reviewer_id = request.reviewer_id.strip()
        record.reviewer_comment = request.reviewer_comment
        record.reviewed_at = now

        db.commit()
        db.refresh(record)

        return self._to_response(record)

    def list_approvals(
        self,
        db: Session,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> OrchestrationApprovalListResponse:
        """Lists historical and pending orchestration approvals."""
        query = db.query(OrchestrationApprovalModel)
        if status:
            query = query.filter(OrchestrationApprovalModel.status == status.upper().strip())

        total = query.count()
        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, offset)

        records = (
            query.order_by(desc(OrchestrationApprovalModel.created_at))
            .offset(safe_offset)
            .limit(safe_limit)
            .all()
        )

        return OrchestrationApprovalListResponse(
            total=total,
            items=[self._to_response(r) for r in records]
        )

    def _to_response(self, record: OrchestrationApprovalModel) -> OrchestrationApprovalResponse:
        """Converts an ORM approval model into a Pydantic response."""
        return OrchestrationApprovalResponse(
            id=record.id,
            approval_id=record.approval_id,
            recommendation_id=record.recommendation_id,
            task_id=record.task_id,
            status=ApprovalStatus(record.status),
            reviewer_id=record.reviewer_id,
            reviewer_comment=record.reviewer_comment,
            original_recommendation=record.original_recommendation or {},
            modifications=record.modifications,
            reviewed_at=record.reviewed_at,
            created_at=record.created_at
        )


orchestration_approval_service = OrchestrationApprovalService()
