"""SQLAlchemy model for historical inspection records."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


class InspectionRecord(Base):
    """Represents a historical visual, ultrasonic, or autonomous inspection event."""
    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    component_id: Mapped[str] = mapped_column(String(64), ForeignKey("components.component_id", ondelete="CASCADE"), index=True, nullable=False)
    inspection_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    inspection_method: Mapped[str] = mapped_column(String(64), nullable=False)
    defect_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    findings: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), default="production", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    component: Mapped["Component"] = relationship("Component", back_populates="inspection_records")
