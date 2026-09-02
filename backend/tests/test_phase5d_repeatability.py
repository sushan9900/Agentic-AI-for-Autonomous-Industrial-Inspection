"""Unit tests for Phase 5D repeatability and deterministic consistency checks."""

import pytest
from scripts.evaluation.performance_metrics import check_deterministic_consistency


def test_deterministic_consistency_all_match():
    detection_counts = [3, 3, 3, 3, 3]
    risk_scores = [100, 100, 100, 100, 100]
    actions = ["URGENT_ENGINEERING_REVIEW"] * 5
    review_statuses = ["PENDING_HUMAN_REVIEW"] * 5

    assert check_deterministic_consistency(detection_counts) is True
    assert check_deterministic_consistency(risk_scores) is True
    assert check_deterministic_consistency(actions) is True
    assert check_deterministic_consistency(review_statuses) is True


def test_deterministic_consistency_flags_variance():
    # If a non-deterministic component changes risk score
    risk_scores = [100, 100, 85, 100, 100]
    assert check_deterministic_consistency(risk_scores) is False

    # If action fluctuates
    actions = ["URGENT_ENGINEERING_REVIEW", "PRIORITY_MAINTENANCE"]
    assert check_deterministic_consistency(actions) is False

    # If review gate is bypassed
    review_statuses = ["PENDING_HUMAN_REVIEW", "APPROVED"]
    assert check_deterministic_consistency(review_statuses) is False
