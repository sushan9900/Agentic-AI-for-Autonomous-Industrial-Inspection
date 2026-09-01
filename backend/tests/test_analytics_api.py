"""API tests for /api/v1/analytics endpoints (Phase 3A)."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_analytics_overview_api():
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_assets"] >= 4
    assert data["total_inspections"] >= 3
    assert data["total_detected_defects"] >= 3
    assert "recent_inspections" in data


def test_get_defect_analytics_api():
    response = client.get("/api/v1/analytics/defects")
    assert response.status_code == 200
    data = response.json()
    assert data["total_defects"] >= 3
    assert "crack" in data["defects_by_type"]
    assert "top_affected_assets" in data


def test_get_risk_analytics_api():
    response = client.get("/api/v1/analytics/risk")
    assert response.status_code == 200
    data = response.json()
    assert "risk_band_distribution" in data
    assert "high_risk_assets" in data
    assert data["average_fleet_risk_score"] > 0
