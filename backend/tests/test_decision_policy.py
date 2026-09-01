"""Unit tests for deterministic decision policy engine (Phase 3B)."""

import pytest
from backend.app.agents.decision_policy import decision_policy_engine


def test_decision_policy_urgent_engineering_review():
    outcome = decision_policy_engine.evaluate(
        defect_count=2,
        max_confidence=0.88,
        max_affected_area_percentage=4.5,
        max_crack_length_pixels=250.0,
        risk_score=85,
        risk_level="CRITICAL",
        triggered_rules=["RULE-CRACK-PL-001 (CRITICAL)"]
    )
    assert outcome.action == "URGENT_ENGINEERING_REVIEW"
    assert outcome.priority == "CRITICAL"
    assert "Severe defect telemetry" in outcome.rationale


def test_decision_policy_priority_maintenance():
    outcome = decision_policy_engine.evaluate(
        defect_count=1,
        max_confidence=0.80,
        max_affected_area_percentage=1.8,
        max_crack_length_pixels=110.0,
        risk_score=60,
        risk_level="HIGH",
        triggered_rules=["RULE-CRACK-PL-003 (MEDIUM)"],
        recurrence_count=2
    )
    assert outcome.action == "PRIORITY_MAINTENANCE"
    assert outcome.priority == "HIGH"


def test_decision_policy_plan_maintenance():
    outcome = decision_policy_engine.evaluate(
        defect_count=1,
        max_confidence=0.65,
        max_affected_area_percentage=0.8,
        max_crack_length_pixels=50.0,
        risk_score=35,
        risk_level="MEDIUM",
        triggered_rules=[]
    )
    assert outcome.action == "PLAN_MAINTENANCE"
    assert outcome.priority == "MEDIUM"


def test_decision_policy_schedule_inspection_marginal():
    outcome = decision_policy_engine.evaluate(
        defect_count=1,
        max_confidence=0.40,
        max_affected_area_percentage=0.3,
        max_crack_length_pixels=20.0,
        risk_score=18,
        risk_level="LOW",
        triggered_rules=[]
    )
    assert outcome.action == "SCHEDULE_INSPECTION"
    assert outcome.priority == "LOW"


def test_decision_policy_monitor_clean():
    outcome = decision_policy_engine.evaluate(
        defect_count=0,
        max_confidence=0.0,
        max_affected_area_percentage=0.0,
        max_crack_length_pixels=0.0,
        risk_score=10,
        risk_level="LOW",
        triggered_rules=[]
    )
    assert outcome.action == "MONITOR"
    assert outcome.priority == "LOW"


def test_decision_policy_insufficient_evidence():
    outcome = decision_policy_engine.evaluate(
        defect_count=0,
        max_confidence=0.0,
        max_affected_area_percentage=0.0,
        max_crack_length_pixels=0.0,
        risk_score=0,
        risk_level="LOW",
        triggered_rules=[],
        evidence_valid=False
    )
    assert outcome.action == "INSUFFICIENT_EVIDENCE"
