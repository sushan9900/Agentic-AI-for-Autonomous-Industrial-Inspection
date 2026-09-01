"""Unit tests for explicit agent failure modes and safe handling (Phase 3B)."""

import json
from pathlib import Path
import pytest
from backend.app.agents.inspection_agent import (
    AssetNotFoundError,
    VisionEvidenceInvalidError,
    inspection_decision_agent,
)
from backend.app.agents.validators import AgentValidator, LLMInvalidOutputError
from backend.app.database.session import SessionLocal

EVIDENCE_FILE = Path("experiments/vision/deepcrack/inference/evidence/11112.evidence.json")


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_invalid_vision_evidence_raises_error(db_session):
    with pytest.raises(VisionEvidenceInvalidError):
        inspection_decision_agent.run_inspection(
            inspection_id="insp-fail-01",
            asset_id="ASSET-PL-01",
            evidence={"invalid_key": "not_vision_evidence"},
            db=db_session
        )


def test_missing_asset_raises_asset_not_found(db_session):
    assert EVIDENCE_FILE.exists()
    with open(EVIDENCE_FILE, "r", encoding="utf-8") as f:
        evidence_dict = json.load(f)

    with pytest.raises(AssetNotFoundError):
        inspection_decision_agent.run_inspection(
            inspection_id="insp-fail-02",
            asset_id="NONEXISTENT-ASSET-404",
            evidence=evidence_dict,
            db=db_session
        )


def test_llm_json_validator_repairs_or_raises():
    # Valid markdown JSON
    valid_md = '```json\n{"recommended_action": "Inspect"}\n```'
    parsed = AgentValidator.parse_and_validate_llm_json(valid_md)
    assert parsed["recommended_action"] == "Inspect"

    # Embedded braces
    embedded = 'Here is the output: {"action": "Repair", "priority": "HIGH"} Thank you.'
    parsed_emb = AgentValidator.parse_and_validate_llm_json(embedded)
    assert parsed_emb["action"] == "Repair"

    # Malformed unrecoverable text raises LLMInvalidOutputError
    with pytest.raises(LLMInvalidOutputError):
        AgentValidator.parse_and_validate_llm_json("This is purely conversational text with no JSON braces.")
