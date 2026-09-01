"""Unit tests for Phase 2B context retrieval services and data aggregation."""

import pytest
from backend.app.database.session import SessionLocal
from backend.app.schemas.context import HistoricalContext
from backend.app.services.context.context_service import context_service
from backend.app.services.context.incident_service import get_relevant_incidents
from backend.app.services.context.inspection_history_service import (
    get_component_inspection_history,
    get_component_work_orders,
)
from backend.app.services.context.maintenance_service import get_component_maintenance_history


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_get_component_context_success(db):
    context = context_service.get_component_context(db, "PIPE-SEG-4021")
    assert context is not None
    assert isinstance(context, HistoricalContext)
    assert context.schema_version == "1.0"
    assert context.component.component_id == "PIPE-SEG-4021"
    assert context.asset.asset_id == "ASSET-PL-01"
    assert len(context.maintenance_history) >= 2
    assert len(context.previous_inspections) >= 2
    assert len(context.previous_work_orders) >= 1
    assert len(context.relevant_incidents) >= 1
    assert context.is_synthetic_data is True
    assert context.source_references["database_provider"] == "PostgreSQL"


def test_get_component_context_not_found(db):
    context = context_service.get_component_context(db, "NON-EXISTENT-COMPONENT-ID")
    assert context is None


def test_maintenance_service_query(db):
    records = get_component_maintenance_history(db, "PIPE-SEG-4021")
    assert len(records) >= 2
    # Verify order is descending by performed_at
    assert records[0].performed_at >= records[1].performed_at


def test_inspection_history_service_query(db):
    inspections = get_component_inspection_history(db, "PIPE-SEG-4021")
    assert len(inspections) >= 2
    work_orders = get_component_work_orders(db, "PIPE-SEG-4021")
    assert len(work_orders) >= 1


def test_incident_service_query(db):
    incidents = get_relevant_incidents(db, component_type="PIPE_SEGMENT", limit=5)
    assert len(incidents) >= 1
    assert incidents[0].component_type == "PIPE_SEGMENT"
