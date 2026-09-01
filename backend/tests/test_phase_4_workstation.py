"""Unit and API Integration Test Suite for Phase 4 Inspector Review Workstation."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.database.models.agent_decision import (
    AgentDecisionModel,
    AgentReasoningTraceModel,
)
from backend.app.database.session import SessionLocal
from backend.app.main import app
from backend.app.schemas.agent_decision import AgentInspectionDecision

client = TestClient(app)

REAL_TEST_IMAGE = Path("data/processed/deepcrack/yolo/images/test/11112.jpg")
EVIDENCE_FILE = Path("experiments/vision/deepcrack/inference/evidence/11112.evidence.json")


@pytest.fixture(scope="module", autouse=True)
def setup_test_decision():
    """Seeds a test decision for Phase 4 API testing and cleans up afterwards."""
    session = SessionLocal()
    test_dec_id = "dec-insp-phase4-test-ASSET-PL-01"

    # Cleanup prior
    session.query(AgentReasoningTraceModel).filter(AgentReasoningTraceModel.decision_id == test_dec_id).delete()
    session.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == test_dec_id).delete()
    session.commit()

    # Seed test decision
    with open(EVIDENCE_FILE, "r", encoding="utf-8") as f:
        ev_dict = json.load(f)

    payload = {
        "inspection_id": "insp-phase4-test",
        "asset_id": "ASSET-PL-01",
        "evidence": ev_dict
    }
    res = client.post("/api/v1/agent/inspect", json=payload)
    assert res.status_code == 200

    yield test_dec_id

    # Teardown
    session.query(AgentReasoningTraceModel).filter(AgentReasoningTraceModel.decision_id == test_dec_id).delete()
    session.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == test_dec_id).delete()
    session.commit()
    session.close()


def test_1_list_agent_decisions():
    response = client.get("/api/v1/agent/decisions?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_2_filter_decisions_by_risk_and_status(setup_test_decision):
    # Filter by CRITICAL risk
    res_crit = client.get("/api/v1/agent/decisions?risk_level=CRITICAL")
    assert res_crit.status_code == 200
    data_crit = res_crit.json()
    for item in data_crit["items"]:
        assert item["risk_level"] == "CRITICAL"

    # Filter by review status
    res_pending = client.get("/api/v1/agent/decisions?review_status=PENDING_HUMAN_REVIEW")
    assert res_pending.status_code == 200
    data_pending = res_pending.json()
    for item in data_pending["items"]:
        assert item["review_status"] == "PENDING_HUMAN_REVIEW"


def test_3_get_agent_decision_detail(setup_test_decision):
    decision_id = setup_test_decision
    response = client.get(f"/api/v1/agent/decisions/{decision_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["decision_id"] == decision_id
    assert data["review_status"] == "PENDING_HUMAN_REVIEW"
    assert data["operational_decision"] == "URGENT_ENGINEERING_REVIEW"


def test_4_submit_human_review_approval(setup_test_decision):
    decision_id = setup_test_decision
    review_payload = {
        "reviewer_name": "Lead Inspector S. Ray",
        "review_action": "APPROVED",
        "review_comment": "Verified crack length and urgent NDE requirements."
    }

    response = client.post(f"/api/v1/agent/decisions/{decision_id}/review", json=review_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision_id"] == decision_id
    assert data["review_status"] == "APPROVED"
    assert data["reviewer_name"] == "Lead Inspector S. Ray"
    assert data["review_action"] == "APPROVED"
    assert data["reviewed_at"] is not None


def test_5_submit_human_review_invalid_action(setup_test_decision):
    decision_id = setup_test_decision
    invalid_payload = {
        "reviewer_name": "Inspector S. Ray",
        "review_action": "INVALID_ACTION_NAME",
        "review_comment": "Testing error."
    }
    response = client.post(f"/api/v1/agent/decisions/{decision_id}/review", json=invalid_payload)
    assert response.status_code == 400
    assert "Invalid review action" in response.json()["detail"]


def test_6_submit_review_nonexistent_decision():
    payload = {
        "reviewer_name": "Inspector",
        "review_action": "APPROVED"
    }
    response = client.post("/api/v1/agent/decisions/nonexistent-dec-999/review", json=payload)
    assert response.status_code == 404


def test_7_get_overview_kpis():
    response = client.get("/api/v1/agent/kpis")
    assert response.status_code == 200
    data = response.json()
    assert "total_inspections" in data
    assert "pending_reviews" in data
    assert "critical_findings" in data
    assert "approved_count" in data


def test_8_get_system_status():
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "HEALTHY"
    assert data["database"] == "CONNECTED"
    assert data["vision_model"] == "LOADED"
    assert data["llm_model"] == "gemma3:latest"
    assert "device" in data


def test_9_upload_and_inspect_unsupported_format():
    files = {"file": ("test.txt", b"not an image", "text/plain")}
    data = {"asset_id": "ASSET-PL-01"}
    response = client.post("/api/v1/agent/upload-and-inspect", files=files, data=data)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_10_upload_and_inspect_empty_file():
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    data = {"asset_id": "ASSET-PL-01"}
    response = client.post("/api/v1/agent/upload-and-inspect", files=files, data=data)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
