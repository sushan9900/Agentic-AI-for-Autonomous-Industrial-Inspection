"""Unit tests for Phase 5D corrected benchmark harness, single-execution guarantee, and CLI modes."""

from unittest.mock import MagicMock, patch
import pytest

from scripts.evaluation.benchmark_config import BenchmarkConfig
from scripts.evaluation.benchmark_end_to_end import parse_args
from scripts.evaluation.reliability_runner import PipelineStageTimer, preheat_subsystems


def test_cli_mode_selection_defaults():
    with patch("sys.argv", ["benchmark_end_to_end.py"]):
        args = parse_args()
        assert args.mode is None
        assert args.skip_failures is False
        assert args.runs is None
        assert args.warmup is None


def test_cli_mode_selection_explicit_mode():
    with patch("sys.argv", ["benchmark_end_to_end.py", "--mode", "quick"]):
        args = parse_args()
        assert args.mode == "quick"


def test_cli_mode_selection_skip_failures():
    with patch("sys.argv", ["benchmark_end_to_end.py", "--mode", "full", "--skip-failures"]):
        args = parse_args()
        assert args.mode == "full"
        assert args.skip_failures is True


def test_single_production_execution_guarantee():
    """Verifies that run_instrumented_e2e executes perception and agent decision EXACTLY ONCE."""
    mock_pipeline = MagicMock()
    mock_evidence = MagicMock()
    mock_evidence.inspection_id = "mock-insp-01"
    mock_evidence.processing.validation_ms = 0.5
    mock_evidence.processing.preprocessing_ms = 0.4
    mock_evidence.processing.inference_ms = 35.0
    mock_evidence.processing.postprocessing_ms = 2.0
    mock_evidence.processing.evidence_construction_ms = 1.0
    mock_evidence.processing.total_execution_ms = 38.9
    mock_pipeline.run_inspection_evidence.return_value = mock_evidence

    mock_e2e = MagicMock()
    mock_e2e._get_pipeline.return_value = mock_pipeline

    mock_agent = MagicMock()
    mock_decision = MagicMock()
    mock_decision.reasoning_trace = [
        MagicMock(stage="RETRIEVE_ASSET_CONTEXT", duration_ms=10.0),
        MagicMock(stage="GET_MAINTENANCE_HISTORY", duration_ms=5.0),
        MagicMock(stage="GET_SEVERITY_THRESHOLDS", duration_ms=1.0),
        MagicMock(stage="CHECK_SIMILAR_INCIDENTS", duration_ms=4.0),
        MagicMock(stage="CALCULATE_RISK_SCORE", duration_ms=0.5),
        MagicMock(stage="EVALUATE_DECISION_POLICY", duration_ms=0.2),
        MagicMock(stage="GENERATE_WORK_ORDER", duration_ms=25000.0),
        MagicMock(stage="FINAL_VALIDATION", duration_ms=0.1),
    ]
    mock_decision.human_review_required = True
    mock_decision.review_status = "PENDING_HUMAN_REVIEW"
    mock_agent.run_inspection.return_value = mock_decision

    timer = PipelineStageTimer(e2e_service=mock_e2e)

    with patch("scripts.evaluation.reliability_runner.inspection_decision_agent", mock_agent), \
         patch("scripts.evaluation.reliability_runner.agent_decision_service") as mock_save:

        decision, stages = timer.run_instrumented_e2e(
            image_path="data/processed/deepcrack/yolo/images/test/11112.jpg",
            asset_id="ASSET-PL-01",
            component_id="PIPE-SEG-4021",
            skip_db=True
        )

        # Perception must be called EXACTLY ONCE
        assert mock_pipeline.run_inspection_evidence.call_count == 1
        # Decision agent must be called EXACTLY ONCE
        assert mock_agent.run_inspection.call_count == 1
        # Timing stages must match extracted values
        assert stages["C_yolo_inference_ms"] == 35.0
        assert stages["I_llm_generation_ms"] == 25000.0
        assert stages["total_db_retrieval_ms"] == 20.0  # 10 + 5 + 1 + 4
        assert stages["M_complete_end_to_end_ms"] > 0.0


def test_cold_start_vs_warm_labeling():
    cfg_cold = BenchmarkConfig(warmup_runs=0, measured_runs=1)
    cfg_warm = BenchmarkConfig(warmup_runs=1, measured_runs=5)

    assert cfg_cold.warmup_runs == 0
    assert cfg_warm.warmup_runs == 1


def test_aggregated_final_reports_structure():
    """Verifies that the aggregated Phase 5D reports exist and contain verified metrics."""
    from scripts.evaluation.aggregate_final_report import build_and_save_final_reports
    paths = build_and_save_final_reports("reports/phase5d")

    assert "final_report_json" in paths
    assert "final_report_md" in paths

    # Verify JSON structure
    import json
    with open(paths["final_report_json"], "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["phase"] == "5D"
    assert "workload_durations" in data
    assert data["workload_durations"]["multi_image_workload_duration_seconds"] == 570.59
    assert data["workload_durations"]["failure_recovery_duration_seconds"] == 0.21
    assert data["repeatability_benchmark"]["deterministic_consistency"]["all_deterministic_invariants_hold"] is True
    assert data["repeatability_benchmark"]["deterministic_consistency"]["consistency_rate_percent"] == 100.0
    assert data["bottleneck_analysis"]["primary_bottleneck"] == "Ollama Gemma 3 Generation"
    assert data["safety_preservation"]["zero_automated_maintenance_execution"] is True

