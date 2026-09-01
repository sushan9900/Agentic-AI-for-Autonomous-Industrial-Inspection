"""SQLAlchemy model for physical industrial assets."""

from datetime import date
from typing import List, Optional
from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base, TimestampMixin


class Asset(Base, TimestampMixin):
    """Represents a primary physical industrial asset (e.g. Pipeline Loop, Storage Tank, Pressure Vessel)."""
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    asset_code: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    installation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    location: Mapped[str] = mapped_column(String(256), nullable=False)
    operational_status: Mapped[str] = mapped_column(String(32), index=True, default="OPERATIONAL", nullable=False)
    warranty_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warranty_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), default="production", nullable=False)

    # Relationships
    components: Mapped[List["Component"]] = relationship("Component", back_populates="asset", cascade="all, delete-orphan")
    defects: Mapped[List["DefectRecord"]] = relationship("DefectRecord", back_populates="asset", cascade="all, delete-orphan")
