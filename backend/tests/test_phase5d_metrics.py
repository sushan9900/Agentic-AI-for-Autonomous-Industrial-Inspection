"""Unit tests for Phase 5D performance metrics, percentiles, and throughput calculations."""

import pytest
from scripts.evaluation.performance_metrics import (
    check_deterministic_consistency,
    compute_regression_comparison,
    compute_stats,
    compute_throughput,
)


def test_compute_stats_basic():
    samples = [10.0, 20.0, 30.0, 40.0, 50.0]
    stats = compute_stats(samples)
    assert stats["count"] == 5
    assert stats["min"] == 10.0
    assert stats["max"] == 50.0
    assert stats["mean"] == 30.0
    assert stats["median"] == 30.0
    assert stats["stddev"] > 0.0
    assert stats["p95"] == 50.0


def test_compute_stats_insufficient_samples_for_p95():
    samples = [100.0, 200.0]
    stats = compute_stats(samples)
    assert stats["count"] == 2
    assert stats["p95"] == "INSUFFICIENT_SAMPLES"


def test_compute_stats_empty():
    stats = compute_stats([])
    assert stats["count"] == 0
    assert stats["mean"] == 0.0
    assert stats["p95"] == "NOT_AVAILABLE"


def test_compute_throughput_valid():
    tp = compute_throughput(mean_latency_seconds=2.0)
    assert tp["mean_latency_seconds"] == 2.0
    assert tp["images_per_second"] == 0.5
    assert tp["images_per_minute"] == 30.0


def test_compute_throughput_zero():
    tp = compute_throughput(mean_latency_seconds=0.0)
    assert tp["images_per_second"] == 0.0
    assert tp["images_per_minute"] == 0.0


def test_compute_regression_comparison():
    comp = compute_regression_comparison(current_mean_ms=25000.0, baseline_mean_ms=27262.21)
    assert comp["is_faster"] is True
    assert comp["is_slower"] is False
    assert comp["delta_ms"] < 0.0
    assert comp["percentage_change"] < 0.0


def test_check_deterministic_consistency():
    assert check_deterministic_consistency([100, 100, 100, 100]) is True
    assert check_deterministic_consistency(["CRITICAL", "CRITICAL"]) is True
    assert check_deterministic_consistency([100, 95, 100]) is False
    assert check_deterministic_consistency([]) is True
