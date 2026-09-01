"""SQLAlchemy 2.x ORM models for Human-in-the-Loop inspection reviews and audit logging (Phase 2D/3A)."""

from datetime import datetime, timezone
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from backend.app.database.base import Base, TimestampMixin


class InspectionReview(Base, TimestampMixin):
    """Authoritative persistent record of a human-in-the-loop inspection review."""
    __tablename__ = "inspection_reviews"

    review_id = Column(String(64), primary_key=True, index=True)
    inspection_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=True, index=True)
    component_id = Column(String(64), ForeignKey("components.component_id"), nullable=False, index=True)
    assessment_id = Column(String(64), nullable=False, index=True)
    
    # Review Lifecycle State
    status = Column(String(32), nullable=False, default="PENDING_HUMAN_REVIEW", index=True)
    priority = Column(String(32), nullable=False, default="MEDIUM", index=True)
    
    # Reviewer Information
    reviewer_id = Column(String(64), nullable=True)
    reviewer_name = Column(String(128), nullable=True)
    reviewer_comments = Column(Text, nullable=True)
    
    # Immutable AI Provenance Snapshots (JSON)
    original_vision_evidence = Column(JSON, nullable=False)
    original_decision = Column(JSON, nullable=False)
    original_assessment = Column(JSON, nullable=False)
    original_draft_work_order = Column(JSON, nullable=False)
    reasoning_trace = Column(JSON, nullable=False)
    
    # Human-Edited Work Order Snapshot (JSON, null if unedited)
    edited_work_order = Column(JSON, nullable=True)
    
    # Review Timestamp
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    component = relationship("Component", backref="reviews")
    asset = relationship("Asset", backref="reviews")
    audit_logs = relationship(
        "ReviewAuditLog",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewAuditLog.created_at"
    )

    __table_args__ = (
        Index("ix_inspection_reviews_comp_status", "component_id", "status"),
        Index("ix_inspection_reviews_asset_status", "asset_id", "status"),
    )


class ReviewAuditLog(Base):
    """Immutable append-only audit trail recording every state change and inspector action."""
    __tablename__ = "review_audit_logs"

    audit_id = Column(String(64), primary_key=True, index=True)
    review_id = Column(
        String(64),
        ForeignKey("inspection_reviews.review_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_type = Column(String(64), nullable=False, index=True)
    reviewer_id = Column(String(64), nullable=True)
    reviewer_name = Column(String(128), nullable=True)
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)
    change_summary = Column(Text, nullable=True)
    metadata_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    review = relationship("InspectionReview", back_populates="audit_logs")
