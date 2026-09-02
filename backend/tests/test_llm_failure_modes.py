"""Unit tests for the 12 LLM failure modes (Phase 5C)."""

import pytest
from backend.app.agents.validators import AgentValidator, LLMInvalidOutputError
from backend.app.evaluation.llm_cases import get_llm_failure_mode_cases
from backend.app.evaluation.llm_evaluator import LLMReliabilityEvaluator


@pytest.fixture
def evaluator():
    return LLMReliabilityEvaluator()


def test_failure_mode_cases_count():
    cases = get_llm_failure_mode_cases()
    assert len(cases) == 12


def test_evaluate_all_failure_modes(evaluator):
    res = evaluator.evaluate_failure_modes()
    assert res["total_failure_cases"] == 12
    assert res["passed_failure_cases"] == 12
    assert res["pass_rate"] == 1.0


def test_malformed_json_failure_mode():
    with pytest.raises(LLMInvalidOutputError):
        AgentValidator.parse_and_validate_llm_json("NOT A VALID JSON STRING")


def test_empty_response_failure_mode():
    with pytest.raises(LLMInvalidOutputError):
        AgentValidator.parse_and_validate_llm_json("   ")


def test_attempted_overrides_stripped():
    raw_payload = {
        "recommended_action": "Conduct inspection",
        "engineering_justification": "Crack detected",
        "risk_score": 10,
        "risk_level": "LOW",
        "operational_decision": "MONITOR",
        "human_review_required": False,
        "review_status": "APPROVED",
        "status": "COMPLETED"
    }

    sanitized, warnings = AgentValidator.sanitize_and_ground_work_order(
        llm_raw_data=raw_payload,
        expected_inspection_id="insp-01",
        expected_image_filename="11112.jpg",
        expected_image_sha256="abc12345",
        cost_data_available=False
    )

    assert "risk_score" not in sanitized
    assert "risk_level" not in sanitized
    assert "operational_decision" not in sanitized
    assert "human_review_required" not in sanitized
    assert "review_status" not in sanitized
    assert len(warnings) >= 5
