"""Unit tests for AgentDecisionEvaluator and decision case matching (Phase 5B)."""

import pytest
from backend.app.evaluation.agent_evaluator import AgentDecisionEvaluator
from backend.app.evaluation.decision_cases import get_evaluation_cases


@pytest.fixture
def evaluator():
    return AgentDecisionEvaluator()


def test_get_evaluation_cases():
    cases = get_evaluation_cases()
    assert len(cases) >= 11
    case_ids = [c.case_id for c in cases]
    assert "CASE-01-CRITICAL-DEFECT" in case_ids
    assert "CASE-05-NO-DEFECT-MONITOR" in case_ids
    assert "CASE-06-INSUFFICIENT-EVIDENCE" in case_ids


def test_evaluate_decision_cases(evaluator):
    res = evaluator.evaluate_decision_cases()
    assert res["total_cases"] >= 11
    assert res["matched_cases"] == res["total_cases"]
    assert res["accuracy"] == 1.0
    for case_res in res["cases"]:
        assert case_res["consistency_status"] == "CONSISTENT"
        assert case_res["action_matched"] is True
        assert case_res["priority_matched"] is True


def test_evaluate_risk_scoring(evaluator):
    risk_res = evaluator.evaluate_risk_scoring()
    assert risk_res["all_risk_tests_passed"] is True
    assert risk_res["total_risk_tests"] >= 3


def test_evaluate_repeatability(evaluator):
    repeat_res = evaluator.evaluate_repeatability(num_cycles=10)
    assert repeat_res["is_100_percent_repeatable"] is True
    assert repeat_res["repeatability_failures"] == 0


def test_compute_confusion_matrix(evaluator):
    case_records = [
        {"expected_action": "URGENT_ENGINEERING_REVIEW", "actual_action": "URGENT_ENGINEERING_REVIEW"},
        {"expected_action": "MONITOR", "actual_action": "MONITOR"}
    ]
    cm = evaluator.compute_confusion_matrix(case_records)
    assert "matrix" in cm
    assert "per_class_accuracy" in cm
    assert cm["matrix"]["URGENT_ENGINEERING_REVIEW"]["URGENT_ENGINEERING_REVIEW"] == 1
    assert cm["matrix"]["MONITOR"]["MONITOR"] == 1
