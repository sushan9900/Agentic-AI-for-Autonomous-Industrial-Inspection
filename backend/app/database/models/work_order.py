"""SQLAlchemy model for maintenance work orders."""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


class WorkOrder(Base):
    """Represents a historical or active industrial maintenance work order."""
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    component_id: Mapped[str] = mapped_column(String(64), ForeignKey("components.component_id", ondelete="CASCADE"), index=True, nullable=False)
    inspection_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    priority: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="PENDING_APPROVAL", nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_team: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    downtime_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), default="production", nullable=False)

    # Relationships
    component: Mapped["Component"] = relationship("Component", back_populates="work_orders")
