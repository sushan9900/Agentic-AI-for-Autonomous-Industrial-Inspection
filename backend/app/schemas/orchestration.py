"""Pydantic v2 schemas for Inspection Orchestration State Machine (Phase 8B)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.inspection_task import ActorType, TaskState


class StateTransitionValidation(BaseModel):
    """Validation result for a prospective state transition."""
    is_valid: bool
    current_state: TaskState
    requested_state: TaskState
    actor_type: ActorType
    allowed: bool
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class OrchestrationAuditEvent(BaseModel):
    """Event representation of an orchestrated task transition audit log entry."""
    event_id: str
    task_id: str
    inspection_id: Optional[str] = None
    previous_state: TaskState
    new_state: TaskState
    actor_type: ActorType
    actor_id: Optional[str] = None
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


class OrchestrationAuditResponse(BaseModel):
    """Envelope response for orchestration audit trail queries."""
    total_events: int
    events: List[OrchestrationAuditEvent] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
