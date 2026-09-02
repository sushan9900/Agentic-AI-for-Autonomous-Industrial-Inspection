"""Unit tests for safety validator, invariants, and risk monotonicity (Phase 5B)."""

import pytest
from backend.app.evaluation.safety_validator import SafetyValidator


@pytest.fixture
def safety_validator():
    return SafetyValidator()


def test_validate_all_invariants(safety_validator):
    res = safety_validator.validate_all_invariants()
    assert res["all_invariants_passed"] is True
    assert res["passed_invariants"] == 8
    assert res["total_invariants"] == 8


def test_individual_invariants(safety_validator):
    assert safety_validator.validate_invariant_01_llm_cannot_override_risk_score()["passed"] is True
    assert safety_validator.validate_invariant_02_llm_cannot_override_operational_action()["passed"] is True
    assert safety_validator.validate_invariant_03_human_review_cannot_be_bypassed()["passed"] is True
    assert safety_validator.validate_invariant_04_invalid_evidence_rejection()["passed"] is True
    assert safety_validator.validate_invariant_05_llm_failure_safety_fallback()["passed"] is True
    assert safety_validator.validate_invariant_06_risk_score_bounds()["passed"] is True
    assert safety_validator.validate_invariant_07_deterministic_repeatability()["passed"] is True
    assert safety_validator.validate_invariant_08_no_automated_maintenance_execution()["passed"] is True


def test_validate_monotonicity(safety_validator):
    mono_res = safety_validator.validate_monotonicity()
    assert mono_res["all_monotonic_checks_passed"] is True
    assert len(mono_res["checks"]) == 5
    for c in mono_res["checks"]:
        assert c["passed"] is True
