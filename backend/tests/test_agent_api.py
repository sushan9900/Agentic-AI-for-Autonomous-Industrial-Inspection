"""API integration tests for /api/v1/agent endpoints (Phase 3B)."""

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

client = TestClient(app)

EVIDENCE_FILE = Path("experiments/vision/deepcrack/inference/evidence/11112.evidence.json")


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_decisions():
    session = SessionLocal()
    session.query(AgentReasoningTraceModel).filter(
        AgentReasoningTraceModel.decision_id.in_([
            "dec-insp-11112-44e62c64-ASSET-PL-01",
            "dec-insp-api-test-01-ASSET-PL-01"
        ])
    ).delete(synchronize_session=False)
    session.query(AgentDecisionModel).filter(
        AgentDecisionModel.decision_id.in_([
            "dec-insp-11112-44e62c64-ASSET-PL-01",
            "dec-insp-api-test-01-ASSET-PL-01"
        ])
    ).delete(synchronize_session=False)
    session.commit()
    yield
    session.query(AgentReasoningTraceModel).filter(
        AgentReasoningTraceModel.decision_id.in_([
            "dec-insp-11112-44e62c64-ASSET-PL-01",
            "dec-insp-api-test-01-ASSET-PL-01"
        ])
    ).delete(synchronize_session=False)
    session.query(AgentDecisionModel).filter(
        AgentDecisionModel.decision_id.in_([
            "dec-insp-11112-44e62c64-ASSET-PL-01",
            "dec-insp-api-test-01-ASSET-PL-01"
        ])
    ).delete(synchronize_session=False)
    session.commit()
    session.close()


def test_run_agent_inspection_api():
    assert EVIDENCE_FILE.exists(), f"Evidence file {EVIDENCE_FILE} must exist"
    with open(EVIDENCE_FILE, "r", encoding="utf-8") as f:
        evidence_dict = json.load(f)

    payload = {
        "inspection_id": "insp-11112-44e62c64",
        "asset_id": "ASSET-PL-01",
        "evidence": evidence_dict
    }

    response = client.post("/api/v1/agent/inspect", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["decision_id"] == "dec-insp-11112-44e62c64-ASSET-PL-01"
    assert data["operational_decision"] == "URGENT_ENGINEERING_REVIEW"
    assert data["human_review_required"] is True
    assert len(data["reasoning_trace"]) == 11
    assert data["work_order"]["status"] == "PENDING_HUMAN_REVIEW"


def test_get_agent_decision_api():
    decision_id = "dec-insp-11112-44e62c64-ASSET-PL-01"
    response = client.get(f"/api/v1/agent/decisions/{decision_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["decision_id"] == decision_id
    assert data["operational_decision"] == "URGENT_ENGINEERING_REVIEW"
    assert len(data["reasoning_trace"]) == 11


def test_get_agent_decision_trace_api():
    decision_id = "dec-insp-11112-44e62c64-ASSET-PL-01"
    response = client.get(f"/api/v1/agent/decisions/{decision_id}/trace")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 11
    assert data[0]["stage"] == "INGEST_EVIDENCE"
    assert data[10]["stage"] == "HUMAN_REVIEW_REQUIRED"


def test_get_nonexistent_decision_404():
    response = client.get("/api/v1/agent/decisions/nonexistent-dec-999")
    assert response.status_code == 404
