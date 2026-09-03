"""SQLAlchemy 2.x ORM model for Human Review Inspection Outcomes (Phase 7B)."""

from datetime import datetime, timezone
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.database.base import Base


class InspectionOutcomeModel(Base):
    """
    Immutable persistent record of an authorized human reviewer outcome.
    Captures verified ground truth and enables adaptive learning analysis.
    """
    __tablename__ = "inspection_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    outcome_id = Column(String(64), unique=True, index=True, nullable=False)
    inspection_id = Column(String(64), index=True, nullable=False)
    asset_id = Column(String(64), ForeignKey("assets.asset_id", ondelete="CASCADE"), index=True, nullable=False)
    component_id = Column(String(64), index=True, nullable=True)

    reviewer_id = Column(String(64), index=True, nullable=False)
    review_status = Column(String(32), index=True, nullable=False)  # APPROVED, CORRECTED, REJECTED

    # Snapshots & Provenance
    ai_prediction_snapshot = Column(JSON, nullable=False)
    confirmed_outcome_snapshot = Column(JSON, nullable=False)
    review_metadata = Column(JSON, nullable=False, default=dict)

    # Timestamps
    reviewed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    asset = relationship("Asset", backref="inspection_outcomes")

    __table_args__ = (
        Index("ix_inspection_outcomes_asset_comp", "asset_id", "component_id"),
        Index("ix_inspection_outcomes_status", "review_status"),
        Index("ix_inspection_outcomes_insp_rev", "inspection_id", "reviewer_id"),
    )
