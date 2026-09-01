"""Pydantic v2 schemas for Human-in-the-Loop review lifecycle and audit logging (Phase 2D)."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.agent_assessment import InspectionAssessmentResponse


class ReviewStatus(str, Enum):
    """Explicit review lifecycle states."""
    PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUESTED = "REVISION_REQUESTED"


class AuditEventType(str, Enum):
    """Audit log event types."""
    REVIEW_CREATED = "REVIEW_CREATED"
    REVIEW_OPENED = "REVIEW_OPENED"
    WORK_ORDER_EDITED = "WORK_ORDER_EDITED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    WORK_ORDER_APPROVED = "WORK_ORDER_APPROVED"
    WORK_ORDER_REJECTED = "WORK_ORDER_REJECTED"


VALID_REVIEW_TRANSITIONS: Dict[ReviewStatus, set] = {
    ReviewStatus.PENDING_HUMAN_REVIEW: {
        ReviewStatus.IN_REVIEW,
        ReviewStatus.APPROVED,
        ReviewStatus.REJECTED,
        ReviewStatus.REVISION_REQUESTED,
    },
    ReviewStatus.IN_REVIEW: {
        ReviewStatus.APPROVED,
        ReviewStatus.REJECTED,
        ReviewStatus.REVISION_REQUESTED,
        ReviewStatus.PENDING_HUMAN_REVIEW,
    },
    ReviewStatus.REVISION_REQUESTED: {
        ReviewStatus.IN_REVIEW,
        ReviewStatus.APPROVED,
        ReviewStatus.REJECTED,
        ReviewStatus.PENDING_HUMAN_REVIEW,
    },
    ReviewStatus.APPROVED: set(),  # Terminal state
    ReviewStatus.REJECTED: set(),  # Terminal state
}


class WorkOrderEditPayload(BaseModel):
    """Editable draft work order fields permitted for human reviewer modification."""
    priority: Optional[str] = Field(default=None, description="Operational priority")
    recommended_action: Optional[str] = Field(default=None, description="Prescribed procedure")
    justification: Optional[str] = Field(default=None, description="Engineering rationale")
    required_inspection: Optional[str] = Field(default=None, description="NDE method")
    suggested_team: Optional[str] = Field(default=None, description="Assigned specialist team")
    estimated_downtime_hours: Optional[float] = Field(default=None, ge=0.0)
    estimated_cost: Optional[float] = Field(default=None, ge=0.0)
    uncertainty: Optional[str] = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class ReviewCreateRequest(BaseModel):
    """Request payload to create a persistent inspection review from an assessment response."""
    assessment_response: InspectionAssessmentResponse
    priority: Optional[str] = Field(default=None, description="Optional override priority")

    model_config = ConfigDict(extra="forbid")


class ReviewUpdateRequest(BaseModel):
    """Request payload to update review notes or edit the draft work order."""
    reviewer_id: Optional[str] = Field(default=None)
    reviewer_name: Optional[str] = Field(default=None)
    reviewer_comments: Optional[str] = Field(default=None)
    edited_work_order: Optional[WorkOrderEditPayload] = Field(default=None)
    status: Optional[ReviewStatus] = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class ReviewActionRequest(BaseModel):
    """Request payload for explicit inspector actions (Approve, Reject, Request Revision)."""
    reviewer_id: str = Field(..., min_length=2, description="Inspector badge or employee ID")
    reviewer_name: str = Field(..., min_length=2, description="Full inspector name")
    comments: str = Field(..., min_length=3, description="Inspector rationale or instructions")
    edited_work_order: Optional[WorkOrderEditPayload] = Field(default=None, description="Optional work order modifications")

    model_config = ConfigDict(extra="forbid")


class ReviewAuditLogRead(BaseModel):
    """Read representation of an immutable audit trail record."""
    audit_id: str
    review_id: str
    event_type: str
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    change_summary: Optional[str] = None
    metadata_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InspectionReviewSummary(BaseModel):
    """Concise inspection review record for dashboard queue listing."""
    review_id: str
    inspection_id: str
    component_id: str
    assessment_id: str
    status: ReviewStatus
    priority: str
    detection_count: int
    max_confidence: float
    quality_blur_score: float
    quality_warnings: List[str]
    source_image_filename: str
    reviewer_name: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InspectionReviewRead(BaseModel):
    """Full detailed inspection review record."""
    review_id: str
    inspection_id: str
    component_id: str
    assessment_id: str
    status: ReviewStatus
    priority: str
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewer_comments: Optional[str] = None
    original_vision_evidence: Dict[str, Any]
    original_decision: Dict[str, Any]
    original_assessment: Dict[str, Any]
    original_draft_work_order: Dict[str, Any]
    edited_work_order: Optional[Dict[str, Any]] = None
    reasoning_trace: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None
    audit_logs: List[ReviewAuditLogRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
