"""Unit tests for deterministic risk scoring tool (Phase 3B)."""

import pytest
from backend.app.tools.risk_scoring import RiskScoreInput, calculate_risk_score_tool


def test_calculate_risk_score_critical_scenario():
    params = RiskScoreInput(
        defect_count=3,
        max_confidence=0.88,
        max_affected_area_percentage=4.8,
        max_crack_length_pixels=320.0,
        service_age_years=6.0,
        has_active_warranty=False,
        recurrence_count=2,
        similar_incident_max_severity="CRITICAL",
        component_criticality="CRITICAL"
    )
    result = calculate_risk_score_tool.execute(params)
    assert result.risk_score >= 75
    assert result.risk_level == "CRITICAL"
    assert len(result.contributing_factors) >= 5
    assert any("crack length" in f.lower() for f in result.contributing_factors)


def test_calculate_risk_score_baseline_clean():
    params = RiskScoreInput(
        defect_count=0,
        max_confidence=0.0,
        max_affected_area_percentage=0.0,
        max_crack_length_pixels=0.0,
        service_age_years=1.0,
        has_active_warranty=True,
        recurrence_count=0,
        component_criticality="LOW"
    )
    result = calculate_risk_score_tool.execute(params)
    assert result.risk_score <= 20
    assert result.risk_level == "LOW"


def test_calculate_risk_score_bounded_0_to_100():
    params = RiskScoreInput(
        defect_count=20,
        max_confidence=0.99,
        max_affected_area_percentage=50.0,
        max_crack_length_pixels=2000.0,
        service_age_years=50.0,
        has_active_warranty=False,
        recurrence_count=10,
        similar_incident_max_severity="CRITICAL",
        component_criticality="CRITICAL"
    )
    result = calculate_risk_score_tool.execute(params)
    assert result.risk_score == 100
    assert result.risk_level == "CRITICAL"
