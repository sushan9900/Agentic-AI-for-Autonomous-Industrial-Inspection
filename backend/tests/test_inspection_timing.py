"""Tests for Deterministic Inspection Timing Recommendation Service (Phase 8D)."""

import pytest
from backend.app.schemas.inspection_task import TimingWindow
from backend.app.services.inspection_timing import inspection_timing_service


def test_critical_deteriorating_requires_immediate():
    """Verifies that CRITICAL risk with DETERIORATING status maps to IMMEDIATE."""
    timing = inspection_timing_service.evaluate_timing(
        risk_score=90,
        severity="CRITICAL",
        deterioration_status="DETERIORATING"
    )
    assert timing.timing_window == TimingWindow.IMMEDIATE
    assert timing.urgency == "CRITICAL"
    assert timing.authoritative is False


def test_critical_stable_requires_within_24_hours():
    """Verifies that CRITICAL risk with STABLE status maps to WITHIN_24_HOURS."""
    timing = inspection_timing_service.evaluate_timing(
        risk_score=85,
        severity="CRITICAL",
        deterioration_status="STABLE"
    )
    assert timing.timing_window == TimingWindow.WITHIN_24_HOURS
    assert timing.urgency == "HIGH"


def test_high_deteriorating_requires_within_24_hours():
    """Verifies that HIGH risk with active DETERIORATING trend maps to WITHIN_24_HOURS."""
    timing = inspection_timing_service.evaluate_timing(
        risk_score=70,
        severity="HIGH",
        deterioration_status="DETERIORATING"
    )
    assert timing.timing_window == TimingWindow.WITHIN_24_HOURS
    assert timing.urgency == "HIGH"


def test_persistent_recurrence_requires_within_7_days():
    """Verifies that persistent defect recurrence maps to WITHIN_7_DAYS."""
    timing = inspection_timing_service.evaluate_timing(
        risk_score=60,
        severity="HIGH",
        deterioration_status="STABLE",
        recurrence_pattern="PERSISTENT"
    )
    assert timing.timing_window == TimingWindow.WITHIN_7_DAYS
    assert timing.urgency == "MEDIUM"


def test_moderate_risk_requires_within_30_days():
    """Verifies that MODERATE/MEDIUM risk maps to WITHIN_30_DAYS."""
    timing = inspection_timing_service.evaluate_timing(
        risk_score=45,
        severity="MEDIUM",
        deterioration_status="STABLE"
    )
    assert timing.timing_window == TimingWindow.WITHIN_30_DAYS
    assert timing.urgency == "LOW"


def test_low_risk_routine():
    """Verifies that low risk with no active concerns maps to ROUTINE."""
    timing = inspection_timing_service.evaluate_timing(
        risk_score=15,
        severity="LOW",
        deterioration_status="STABLE"
    )
    assert timing.timing_window == TimingWindow.ROUTINE
    assert timing.urgency == "LOW"
