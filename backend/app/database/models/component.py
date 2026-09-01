"""SQLAlchemy model for inspectable industrial components."""

from datetime import date
from typing import List, Optional
from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base, TimestampMixin


class Component(Base, TimestampMixin):
    """Represents an inspectable sub-component (e.g. Pipe Segment, Weld Seam, Flange, Valve Body)."""
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    component_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(64), ForeignKey("assets.asset_id", ondelete="CASCADE"), index=True, nullable=False)
    component_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    material: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location_description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    installation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="NORMAL", nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), default="production", nullable=False)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="components")
    maintenance_records: Mapped[List["MaintenanceRecord"]] = relationship("MaintenanceRecord", back_populates="component", cascade="all, delete-orphan")
    inspection_records: Mapped[List["InspectionRecord"]] = relationship("InspectionRecord", back_populates="component", cascade="all, delete-orphan")
    work_orders: Mapped[List["WorkOrder"]] = relationship("WorkOrder", back_populates="component", cascade="all, delete-orphan")
