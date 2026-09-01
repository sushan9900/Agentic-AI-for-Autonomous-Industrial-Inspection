"""SQLAlchemy 2.x ORM model for normalized historical defect records (Phase 3A)."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base, TimestampMixin


class DefectRecord(Base, TimestampMixin):
    """Authoritative normalized physical defect record detected during an inspection."""
    __tablename__ = "defect_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    defect_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    inspection_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(64), ForeignKey("assets.asset_id", ondelete="CASCADE"), index=True, nullable=False)
    component_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("components.component_id", ondelete="SET NULL"), index=True, nullable=True)
    
    defect_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Severity & Geometry Metrics
    affected_area_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bounding_box_area_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    crack_length_pixels: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    crack_width_estimate_pixels: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Provenance
    detection_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    raw_evidence_detection_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), default="production", nullable=False)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="defects")
    component: Mapped[Optional["Component"]] = relationship("Component")

    __table_args__ = (
        Index("ix_defect_records_asset_time", "asset_id", "detection_timestamp"),
        Index("ix_defect_records_type_time", "defect_type", "detection_timestamp"),
    )
