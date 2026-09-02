"""Unit tests for Phase 5D failure recovery and resilient exception handling."""

import pytest
from scripts.evaluation.reliability_runner import BenchmarkReliabilityRunner


@pytest.fixture
def runner():
    return BenchmarkReliabilityRunner()


def test_failure_recovery_suite_count(runner):
    results = runner.run_failure_recovery_tests()
    assert results["total_cases"] == 10
    cases = results["cases"]
    assert len(cases) == 10
    test_ids = [r["test_id"] for r in cases]
    assert "FAIL-TEST-01" in test_ids
    assert "FAIL-TEST-05" in test_ids
    assert "FAIL-TEST-10" in test_ids


def test_failure_recovery_all_pass(runner):
    results = runner.run_failure_recovery_tests()
    assert results["passed_cases"] == 10
    for r in results["cases"]:
        assert r["passed"] is True, f"Failed recovery test: {r['test_id']} - {r['condition']}"


def test_failure_recovery_records_duration(runner):
    results = runner.run_failure_recovery_tests()
    assert "failure_recovery_duration_seconds" in results
    assert results["failure_recovery_duration_seconds"] >= 0.0
