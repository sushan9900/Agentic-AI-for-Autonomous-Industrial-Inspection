"""Statistical metrics, percentile routines, and throughput calculations for Phase 5D."""

import math
import statistics
from typing import Any, Dict, List, Optional, Union


def compute_stats(values: List[float]) -> Dict[str, Union[float, str]]:
    """Calculates min, max, mean, median, standard deviation, and p95 for numeric samples."""
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "stddev": 0.0,
            "p95": "NOT_AVAILABLE"
        }

    n = len(values)
    v_min = round(float(min(values)), 2)
    v_max = round(float(max(values)), 2)
    v_mean = round(float(statistics.mean(values)), 2)
    v_med = round(float(statistics.median(values)), 2)
    v_std = round(float(statistics.stdev(values)), 2) if n > 1 else 0.0

    # 95th Percentile calculation using nearest-rank / linear interpolation
    if n >= 5:
        sorted_vals = sorted(values)
        # Nearest rank formula for p95
        rank = math.ceil(0.95 * n) - 1
        p95_val = round(float(sorted_vals[min(rank, n - 1)]), 2)
    else:
        p95_val = "INSUFFICIENT_SAMPLES"

    return {
        "count": n,
        "min": v_min,
        "max": v_max,
        "mean": v_mean,
        "median": v_med,
        "stddev": v_std,
        "p95": p95_val
    }


def compute_throughput(mean_latency_seconds: float) -> Dict[str, Union[float, str]]:
    """Computes sequential throughput in images per second and images per minute."""
    if mean_latency_seconds <= 0.0:
        return {
            "mean_latency_seconds": 0.0,
            "images_per_second": 0.0,
            "images_per_minute": 0.0,
            "throughput_formula": "images_per_minute = 60.0 / mean_latency_seconds"
        }

    imgs_per_sec = round(1.0 / mean_latency_seconds, 4)
    imgs_per_min = round(60.0 / mean_latency_seconds, 2)

    return {
        "mean_latency_seconds": round(mean_latency_seconds, 2),
        "images_per_second": imgs_per_sec,
        "images_per_minute": imgs_per_min,
        "throughput_formula": "images_per_minute = 60.0 / mean_latency_seconds"
    }


def compute_regression_comparison(current_mean_ms: float, baseline_mean_ms: float) -> Dict[str, Any]:
    """Computes difference and percentage delta between current benchmark and historical baseline."""
    delta_ms = round(current_mean_ms - baseline_mean_ms, 2)
    pct_change = round((delta_ms / baseline_mean_ms) * 100.0, 2) if baseline_mean_ms != 0.0 else 0.0

    return {
        "baseline_mean_ms": round(baseline_mean_ms, 2),
        "current_mean_ms": round(current_mean_ms, 2),
        "delta_ms": delta_ms,
        "percentage_change": pct_change,
        "is_faster": delta_ms < 0.0,
        "is_slower": delta_ms > 0.0
    }


def check_deterministic_consistency(values: List[Any]) -> bool:
    """Returns True if all elements in the list are identical."""
    if not values:
        return True
    first = values[0]
    return all(v == first for v in values)
