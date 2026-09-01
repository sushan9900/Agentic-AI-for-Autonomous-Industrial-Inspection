"""API endpoint tests for component context retrieval (Phase 2B)."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_component_context_endpoint_success():
    response = client.get("/api/v1/components/PIPE-SEG-4021/context")
    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == "1.0"
    assert data["component"]["component_id"] == "PIPE-SEG-4021"
    assert data["asset"]["asset_id"] == "ASSET-PL-01"
    assert len(data["maintenance_history"]) >= 2
    assert len(data["previous_inspections"]) >= 2
    assert len(data["previous_work_orders"]) >= 1
    assert len(data["relevant_incidents"]) >= 1
    assert data["is_synthetic_data"] is True


def test_get_component_context_endpoint_not_found():
    response = client.get("/api/v1/components/NON_EXISTENT_COMPONENT_999/context")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()
