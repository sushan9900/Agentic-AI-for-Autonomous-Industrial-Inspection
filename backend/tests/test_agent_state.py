"""Unit tests for AgentInspectionState contract and JSON serialization (Phase 3B)."""

from datetime import datetime, timezone
import json
import pytest
from backend.app.agents.state import AgentInspectionState
from backend.app.agents.trace import TraceEvent


def test_agent_state_creation_and_fields():
    state = AgentInspectionState(
        inspection_id="insp-test-99",
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        evidence={"inspection_id": "insp-test-99", "detection_count": 2},
        asset_context={"asset_id": "ASSET-PL-01", "name": "Test Pipeline"},
        maintenance_history=[{"maintenance_id": "maint-01", "action_taken": "Inspection"}],
        severity_thresholds=[{"rule_id": "RULE-CRACK-PL-001"}],
        similar_incidents=[{"incident_id": "INC-01"}],
        risk_assessment={"risk_score": 75, "risk_level": "CRITICAL"},
        operational_decision="URGENT_ENGINEERING_REVIEW",
        decision_rationale="Extensive crack length detected.",
        work_order={"work_order_id": "wo-test-99", "status": "PENDING_HUMAN_REVIEW"},
        trace=[
            TraceEvent(
                step=1,
                stage="INGEST_EVIDENCE",
                result_summary="Ingested evidence",
                status="completed"
            )
        ],
        errors=[],
        warnings=["High humidity observed"],
        evidence_gaps=[],
        final_status="PENDING_HUMAN_REVIEW"
    )

    assert state.inspection_id == "insp-test-99"
    assert state.asset_id == "ASSET-PL-01"
    assert state.operational_decision == "URGENT_ENGINEERING_REVIEW"
    assert len(state.trace) == 1
    assert state.final_status == "PENDING_HUMAN_REVIEW"


def test_agent_state_json_serialization():
    state = AgentInspectionState(
        inspection_id="insp-test-json",
        asset_id="ASSET-PL-01",
        trace=[
            TraceEvent(
                step=1,
                stage="INGEST_EVIDENCE",
                result_summary="Completed step 1",
                timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    json_str = state.model_dump_json()
    assert isinstance(json_str, str)
    data = json.loads(json_str)
    assert data["inspection_id"] == "insp-test-json"
    assert data["trace"][0]["stage"] == "INGEST_EVIDENCE"
