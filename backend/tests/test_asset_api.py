"""API tests for /api/v1/assets endpoints (Phase 3A)."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_list_assets_api():
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    assert "asset_id" in data[0]
    assert "current_risk_score" in data[0]


def test_get_asset_detail_api():
    response = client.get("/api/v1/assets/ASSET-PL-01")
    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "ASSET-PL-01"
    assert "components" in data
    assert len(data["components"]) >= 1


def test_get_asset_inspections_api():
    response = client.get("/api/v1/assets/ASSET-PL-01/inspections")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_asset_defects_api():
    response = client.get("/api/v1/assets/ASSET-PL-01/defects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "affected_area_percentage" in data[0]


def test_get_asset_risk_api():
    response = client.get("/api/v1/assets/ASSET-PL-01/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "ASSET-PL-01"
    assert "risk_score" in data
    assert "contributing_factors" in data


def test_get_asset_trends_api():
    response = client.get("/api/v1/assets/ASSET-PL-01/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "ASSET-PL-01"
    assert "time_series" in data
    assert "defect_count_trend" in data


def test_get_asset_timeline_api():
    response = client.get("/api/v1/assets/ASSET-PL-01/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "ASSET-PL-01"
    assert data["events_count"] >= 1
    assert "events" in data
