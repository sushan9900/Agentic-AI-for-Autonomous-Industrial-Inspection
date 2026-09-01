"""Unit tests for Phase 2B SQLAlchemy database models and relational integrity."""

import pytest
from sqlalchemy import select
from backend.app.database.models.asset import Asset
from backend.app.database.models.component import Component
from backend.app.database.models.incident import IncidentRecord
from backend.app.database.models.inspection import InspectionRecord
from backend.app.database.models.maintenance import MaintenanceRecord
from backend.app.database.models.work_order import WorkOrder
from backend.app.database.session import SessionLocal


@pytest.fixture(scope="module")
def db_session():
    """Provides a PostgreSQL database session for model testing."""
    session = SessionLocal()
    yield session
    session.close()


def test_asset_model_query_and_relationships(db_session):
    stmt = select(Asset).where(Asset.asset_id == "ASSET-PL-01")
    asset = db_session.scalar(stmt)
    assert asset is not None
    assert asset.asset_type == "PIPELINE"
    assert len(asset.components) >= 3
    comp_ids = [c.component_id for c in asset.components]
    assert "PIPE-SEG-4021" in comp_ids


def test_component_relationships(db_session):
    stmt = select(Component).where(Component.component_id == "PIPE-SEG-4021")
    comp = db_session.scalar(stmt)
    assert comp is not None
    assert comp.asset is not None
    assert comp.asset.asset_id == "ASSET-PL-01"
    assert len(comp.maintenance_records) >= 2
    assert len(comp.inspection_records) >= 2
    assert len(comp.work_orders) >= 1


def test_maintenance_record_properties(db_session):
    stmt = select(MaintenanceRecord).where(MaintenanceRecord.component_id == "PIPE-SEG-4021")
    records = list(db_session.scalars(stmt).all())
    assert len(records) >= 2
    for r in records:
        assert r.maintenance_type in ("PREVENTIVE_MAINTENANCE", "COATING", "INSPECTION", "REPAIR")
        assert r.source_type == "development_synthetic"
        assert r.performed_at is not None


def test_inspection_record_properties(db_session):
    stmt = select(InspectionRecord).where(InspectionRecord.component_id == "PIPE-SEG-4021")
    records = list(db_session.scalars(stmt).all())
    assert len(records) >= 2
    severities = [r.severity for r in records]
    assert "MEDIUM" in severities or "LOW" in severities or "CRITICAL" in severities


def test_work_order_properties(db_session):
    stmt = select(WorkOrder).where(WorkOrder.component_id == "PIPE-SEG-4021")
    wos = list(db_session.scalars(stmt).all())
    assert len(wos) >= 1
    assert any(w.status == "COMPLETED" for w in wos)
    assert any(w.priority == "MEDIUM" for w in wos)


def test_incident_record_properties(db_session):
    stmt = select(IncidentRecord).where(IncidentRecord.component_type == "PIPE_SEGMENT")
    incidents = list(db_session.scalars(stmt).all())
    assert len(incidents) >= 1
    assert incidents[0].defect_type == "crack"
