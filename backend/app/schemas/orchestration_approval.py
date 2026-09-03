"""Pydantic v2 schemas for Orchestration Human Approval Gate (Phase 8F)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ApprovalStatus(str, Enum):
    """Lifecycle states of an orchestration task approval."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class ApprovalDecisionRequest(BaseModel):
    """Human decision payload to approve, modify, or reject a recommendation."""
    reviewer_id: str = Field(..., min_length=2, max_length=100, description="Identifier of the authorized human engineer")
    status: ApprovalStatus = Field(..., description="Human approval decision: APPROVED, MODIFIED, or REJECTED")
    reviewer_comment: Optional[str] = Field(default=None, max_length=1000, description="Reviewer commentary or justification")
    modifications: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Explicit modifications to task type, priority, or timing window if status is MODIFIED"
    )

    model_config = ConfigDict(extra="forbid")


class OrchestrationApprovalResponse(BaseModel):
    """Full representation of an orchestration approval record."""
    id: int
    approval_id: str
    recommendation_id: str
    task_id: Optional[str] = None
    status: ApprovalStatus
    reviewer_id: Optional[str] = None
    reviewer_comment: Optional[str] = None
    original_recommendation: Dict[str, Any] = Field(default_factory=dict)
    modifications: Optional[Dict[str, Any]] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class OrchestrationApprovalListResponse(BaseModel):
    """Paginated list of orchestration approvals."""
    total: int
    items: List[OrchestrationApprovalResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
