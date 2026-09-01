"""SQLAlchemy model for historical maintenance actions."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


class MaintenanceRecord(Base):
    """Represents a historical maintenance, repair, coating, or service event."""
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    maintenance_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    component_id: Mapped[str] = mapped_column(String(64), ForeignKey("components.component_id", ondelete="CASCADE"), index=True, nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_taken: Mapped[str] = mapped_column(Text, nullable=False)
    technician_team: Mapped[str] = mapped_column(String(128), nullable=False)
    downtime_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), default="production", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    component: Mapped["Component"] = relationship("Component", back_populates="maintenance_records")
