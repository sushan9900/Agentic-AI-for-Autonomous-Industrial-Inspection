"""Benchmark configuration, hardware profiles, and dataset specifications (Phase 5D)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkDatasetItem:
    """Represents a real test image in the benchmark workload."""
    filename: str
    path: str
    expected_sha256: Optional[str] = None
    is_primary: bool = False


@dataclass
class BenchmarkConfig:
    """Master configuration for Phase 5D End-to-End Performance and Reliability Benchmark."""
    primary_image_path: str = "data/processed/deepcrack/yolo/images/test/11112.jpg"
    primary_image_sha256: str = "44e62c6410a898b496e245ac28f3f1604c31acb04cad4e5b0551738f40a78313"
    checkpoint_path: str = "experiments/vision/deepcrack/baseline/weights/best.pt"
    default_asset_id: str = "ASSET-PL-01"
    default_component_id: str = "PIPE-SEG-4021"

    # Execution Mode: full, quick, repeatability, multi-image, failures
    mode: str = "quick"
    skip_failures: bool = False

    # Repeatability settings
    warmup_runs: int = 1
    measured_runs: int = 5

    # Report output paths
    report_md_path: str = "reports/phase5d_end_to_end_performance.md"
    report_json_path: str = "reports/phase5d_end_to_end_performance.json"
    experiments_report_dir: str = "experiments/vision/deepcrack/reports"

    # Historical Phase 5C comparison baseline (Local Ollama Gemma 3)
    phase_5c_baseline: Dict[str, float] = field(default_factory=lambda: {
        "mean_latency_ms": 27262.21,
        "median_latency_ms": 24770.09,
        "min_latency_ms": 23689.42,
        "max_latency_ms": 38442.44
    })

    # Benchmark test dataset: 10 real images from DeepCrack test set
    dataset_items: List[BenchmarkDatasetItem] = field(default_factory=lambda: [
        BenchmarkDatasetItem(
            filename="11112.jpg",
            path="data/processed/deepcrack/yolo/images/test/11112.jpg",
            expected_sha256="44e62c6410a898b496e245ac28f3f1604c31acb04cad4e5b0551738f40a78313",
            is_primary=True
        ),
        BenchmarkDatasetItem(filename="11117.jpg", path="data/processed/deepcrack/yolo/images/test/11117.jpg"),
        BenchmarkDatasetItem(filename="11118.jpg", path="data/processed/deepcrack/yolo/images/test/11118.jpg"),
        BenchmarkDatasetItem(filename="11119.jpg", path="data/processed/deepcrack/yolo/images/test/11119.jpg"),
        BenchmarkDatasetItem(filename="11134-1.jpg", path="data/processed/deepcrack/yolo/images/test/11134-1.jpg"),
        BenchmarkDatasetItem(filename="11134-2.jpg", path="data/processed/deepcrack/yolo/images/test/11134-2.jpg"),
        BenchmarkDatasetItem(filename="11134-3.jpg", path="data/processed/deepcrack/yolo/images/test/11134-3.jpg"),
        BenchmarkDatasetItem(filename="11134-4.jpg", path="data/processed/deepcrack/yolo/images/test/11134-4.jpg"),
        BenchmarkDatasetItem(filename="11134-5.jpg", path="data/processed/deepcrack/yolo/images/test/11134-5.jpg"),
        BenchmarkDatasetItem(filename="11134-6.jpg", path="data/processed/deepcrack/yolo/images/test/11134-6.jpg"),
    ])


default_benchmark_config = BenchmarkConfig()
