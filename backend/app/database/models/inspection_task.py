"""SQLAlchemy ORM models for Inspection Task Lifecycle, Transitions, and Approvals (Phase 8A/8B/8F)."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


class InspectionTaskModel(Base):
    """
    Persistent model representing an operational inspection task.
    Enforces deterministic state transitions and auditable lifecycle tracking.
    """
    __tablename__ = "inspection_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    inspection_id = Column(String(64), nullable=True, index=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=False, index=True)
    component_id = Column(String(64), nullable=True, index=True)

    state = Column(String(32), nullable=False, default="CREATED", index=True)
    task_type = Column(String(32), nullable=False, default="VISUAL_INSPECTION")
    priority = Column(String(16), nullable=False, default="MEDIUM", index=True)
    timing_window = Column(String(32), nullable=False, default="ROUTINE")
    assigned_to = Column(String(64), nullable=True)

    payload = Column(JSON, nullable=True, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    asset = relationship("Asset", backref="inspection_tasks")


class InspectionTaskTransitionModel(Base):
    """
    Immutable historical audit ledger tracking every state transition of an inspection task.
    """
    __tablename__ = "inspection_task_transitions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transition_id = Column(String(64), unique=True, nullable=False, index=True)
    task_id = Column(String(64), nullable=False, index=True)
    inspection_id = Column(String(64), nullable=True, index=True)

    previous_state = Column(String(32), nullable=False)
    new_state = Column(String(32), nullable=False)
    actor_type = Column(String(32), nullable=False)
    actor_id = Column(String(64), nullable=True)
    reason = Column(Text, nullable=False)
    transition_metadata = Column(JSON, nullable=True, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class OrchestrationApprovalModel(Base):
    """
    Human approval audit record for agentic orchestration recommendations.
    Ensures no AI recommendation executes without explicit human authorization.
    """
    __tablename__ = "orchestration_approvals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    approval_id = Column(String(64), unique=True, nullable=False, index=True)
    recommendation_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)

    status = Column(String(32), nullable=False, default="PENDING", index=True)  # PENDING, APPROVED, MODIFIED, REJECTED
    reviewer_id = Column(String(64), nullable=True)
    reviewer_comment = Column(Text, nullable=True)

    original_recommendation = Column(JSON, nullable=False, default=dict)
    modifications = Column(JSON, nullable=True, default=dict)

    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
