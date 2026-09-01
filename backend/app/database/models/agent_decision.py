"""SQLAlchemy 2.x ORM models for Agent Decisions and Reasoning Traces (Phase 3B/4)."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base, TimestampMixin


class AgentDecisionModel(Base, TimestampMixin):
    """Authoritative persistent record of an autonomous inspection decision."""
    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    inspection_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(64), ForeignKey("assets.asset_id", ondelete="CASCADE"), index=True, nullable=False)
    
    operational_decision: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Human-in-the-Loop Review Status (Phase 4)
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING_HUMAN_REVIEW", index=True, nullable=False)
    reviewer_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    review_action: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Immutable Snapshots & Artifacts
    evidence_reference: Mapped[dict] = mapped_column(JSON, nullable=False)
    risk_assessment: Mapped[dict] = mapped_column(JSON, nullable=False)
    work_order: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_gaps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    execution_metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    asset = relationship("Asset", backref="agent_decisions")
    traces: Mapped[List["AgentReasoningTraceModel"]] = relationship(
        "AgentReasoningTraceModel",
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="AgentReasoningTraceModel.step"
    )

    __table_args__ = (
        Index("ix_agent_decisions_asset_op", "asset_id", "operational_decision"),
        Index("ix_agent_decisions_review_status", "review_status"),
    )


class AgentReasoningTraceModel(Base):
    """Immutable persistent trace step of an agent reasoning workflow."""
    __tablename__ = "agent_reasoning_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    decision_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_decisions.decision_id", ondelete="CASCADE"), index=True, nullable=False)
    
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tool: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    decision = relationship("AgentDecisionModel", back_populates="traces")
