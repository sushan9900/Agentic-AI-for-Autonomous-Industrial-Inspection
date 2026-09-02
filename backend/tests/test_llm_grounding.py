"""Unit tests verifying LLM prompt evidence grounding and fact boundaries (Phase 5C)."""

import json
from pathlib import Path
import pytest
from backend.app.agents.prompts import AgentPromptBuilder
from backend.app.evaluation.llm_cases import get_llm_grounding_cases
from vision.schemas.evidence import VisionEvidence

EVIDENCE_FILE = Path("experiments/vision/deepcrack/inference/evidence/11112.evidence.json")


@pytest.fixture
def base_evidence():
    with open(EVIDENCE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return VisionEvidence.model_validate(data)


def test_grounding_cases_specification():
    cases = get_llm_grounding_cases()
    assert len(cases) == 8
    case_ids = [c.case_id for c in cases]
    assert "GROUND-CASE-A" in case_ids
    assert "GROUND-CASE-C" in case_ids
    assert "GROUND-CASE-E" in case_ids


def test_prompt_builder_authoritative_fact_separation(base_evidence):
    prompt = AgentPromptBuilder.build_prompt(
        evidence=base_evidence,
        asset_context={"asset_id": "ASSET-PL-01", "location": "Sector 4"},
        maintenance_history=[],
        severity_thresholds=[],
        similar_incidents=[],
        risk_assessment={"risk_score": 100, "risk_level": "CRITICAL"},
        operational_decision="URGENT_ENGINEERING_REVIEW"
    )

    assert "AUTHORITATIVE_SYSTEM_DECISION" in prompt
    assert "VERIFIED_EVIDENCE_PACKAGE" in prompt
    assert "HISTORICAL_COST_BASELINE" in prompt
    assert "DO NOT change or contradict the AUTHORITATIVE_SYSTEM_DECISION" in prompt


def test_prompt_builder_null_cost_when_history_unavailable(base_evidence):
    prompt = AgentPromptBuilder.build_prompt(
        evidence=base_evidence,
        asset_context={"asset_id": "ASSET-PL-01"},
        maintenance_history=[],
        severity_thresholds=[],
        similar_incidents=[],
        risk_assessment={"risk_score": 25, "risk_level": "MEDIUM"},
        operational_decision="PLAN_MAINTENANCE"
    )

    assert '"cost_data_available": false' in prompt or '"cost_data_available": False' in prompt
    assert '"estimated_cost": null' in prompt
