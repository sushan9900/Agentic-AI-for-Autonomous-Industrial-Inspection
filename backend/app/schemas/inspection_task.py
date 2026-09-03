"""Pydantic v2 schemas for Inspection Task Lifecycle & Orchestration (Phase 8A)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskState(str, Enum):
    """Deterministic states of an inspection task lifecycle."""
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    ASSIGNED_FOR_REVIEW = "ASSIGNED_FOR_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    REVIEWED = "REVIEWED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class ActorType(str, Enum):
    """Authority classifications for state machine actors."""
    SYSTEM_RECOMMENDATION = "SYSTEM_RECOMMENDATION"
    HUMAN_REVIEWER = "HUMAN_REVIEWER"
    SYSTEM_VALIDATION = "SYSTEM_VALIDATION"


class TaskType(str, Enum):
    """Inspection task operational classifications."""
    VISUAL_INSPECTION = "VISUAL_INSPECTION"
    SUPPLEMENTAL_NDE = "SUPPLEMENTAL_NDE"
    RE_INSPECTION = "RE_INSPECTION"
    EXPERT_EVALUATION = "EXPERT_EVALUATION"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"


class TaskPriority(str, Enum):
    """Task urgency priority levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TimingWindow(str, Enum):
    """Recommended execution scheduling window."""
    IMMEDIATE = "IMMEDIATE"
    WITHIN_24_HOURS = "WITHIN_24_HOURS"
    WITHIN_7_DAYS = "WITHIN_7_DAYS"
    WITHIN_30_DAYS = "WITHIN_30_DAYS"
    ROUTINE = "ROUTINE"


class InspectionTaskCreate(BaseModel):
    """Payload to create an inspection task."""
    inspection_id: Optional[str] = Field(default=None, description="Associated existing inspection ID if applicable")
    asset_id: str = Field(..., min_length=2, max_length=100, description="Target industrial asset ID")
    component_id: Optional[str] = Field(default=None, max_length=100, description="Target component ID")
    task_type: TaskType = Field(default=TaskType.VISUAL_INSPECTION)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    timing_window: TimingWindow = Field(default=TimingWindow.ROUTINE)
    assigned_to: Optional[str] = Field(default=None, description="Assigned inspector or specialist ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic, defect, or operational context")

    model_config = ConfigDict(extra="forbid")


class InspectionTaskTransitionRequest(BaseModel):
    """Request to transition an inspection task to a new state."""
    new_state: TaskState = Field(..., description="Requested target lifecycle state")
    actor_type: ActorType = Field(..., description="Type of actor initiating the transition")
    actor_id: Optional[str] = Field(default=None, description="Identifier of the human reviewer or system agent")
    reason: str = Field(..., min_length=3, max_length=1000, description="Justification for the state transition")
    transition_metadata: Dict[str, Any] = Field(default_factory=dict, description="Supporting context or evidence references")

    model_config = ConfigDict(extra="forbid")


class InspectionTaskTransitionResponse(BaseModel):
    """Immutable record of an executed task lifecycle state transition."""
    id: int
    transition_id: str
    task_id: str
    inspection_id: Optional[str] = None
    previous_state: TaskState
    new_state: TaskState
    actor_type: ActorType
    actor_id: Optional[str] = None
    reason: str
    transition_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class InspectionTaskResponse(BaseModel):
    """Full representation of an inspection task with active state and audit history."""
    id: int
    task_id: str
    inspection_id: Optional[str] = None
    asset_id: str
    component_id: Optional[str] = None
    state: TaskState
    task_type: TaskType
    priority: TaskPriority
    timing_window: TimingWindow
    assigned_to: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    transitions: List[InspectionTaskTransitionResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class InspectionTaskListResponse(BaseModel):
    """Paginated list of inspection tasks."""
    total: int = Field(..., ge=0)
    items: List[InspectionTaskResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
