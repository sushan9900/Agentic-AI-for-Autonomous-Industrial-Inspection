"""Executable CLI script to run Phase 5D End-to-End Performance and Reliability Benchmark."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.session import SessionLocal
from scripts.evaluation.benchmark_config import BenchmarkConfig, default_benchmark_config
from scripts.evaluation.benchmark_report import BenchmarkReportGenerator
from scripts.evaluation.performance_metrics import compute_regression_comparison
from scripts.evaluation.reliability_runner import BenchmarkReliabilityRunner
from scripts.evaluation.resource_monitor import ResourceMonitor


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 5D End-to-End Performance & Reliability Benchmark.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["quick", "repeatability", "multi-image", "failures", "full"],
        default=None,
        help="Benchmark execution mode (default: quick, or repeatability if --runs/--warmup supplied)."
    )
    parser.add_argument(
        "--image",
        type=str,
        default=default_benchmark_config.primary_image_path,
        help=f"Target primary image path (default: {default_benchmark_config.primary_image_path})."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=None,
        help="Number of steady-state measured runs (default: 1 for quick, 5 for repeatability/full)."
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=None,
        help="Number of warmup runs (default: 1 for quick/repeatability/full, 0 if disabled)."
    )
    parser.add_argument(
        "--skip-failures",
        action="store_true",
        help="Skip failure recovery tests even in full mode."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports",
        help="Directory to save generated benchmark reports (default: reports)."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Determine mode cleanly
    if args.mode:
        selected_mode = args.mode
    elif args.runs is not None or args.warmup is not None:
        selected_mode = "repeatability"
    else:
        selected_mode = "quick"

    # Default runs and warmup based on mode
    if selected_mode == "quick":
        warmup_runs = args.warmup if args.warmup is not None else 1
        measured_runs = args.runs if args.runs is not None else 1
    elif selected_mode in ("repeatability", "full"):
        warmup_runs = args.warmup if args.warmup is not None else 1
        measured_runs = args.runs if args.runs is not None else 5
    else:
        warmup_runs = args.warmup if args.warmup is not None else 0
        measured_runs = args.runs if args.runs is not None else 0

    print("=" * 80)
    print("PHASE 5D: END-TO-END PERFORMANCE & RELIABILITY BENCHMARK")
    print("=" * 80)
    print(f"Execution Mode       : {selected_mode.upper()}")
    print(f"Target Primary Image : {args.image}")
    print(f"Warmup Iterations    : {warmup_runs} ({'ENABLED' if warmup_runs > 0 else 'DISABLED - COLD START'})")
    print(f"Measured Iterations  : {measured_runs}")
    print(f"Report Output Dir    : {args.output}")
    print("-" * 80)

    config = BenchmarkConfig(
        mode=selected_mode,
        primary_image_path=args.image,
        warmup_runs=warmup_runs,
        measured_runs=measured_runs,
        skip_failures=args.skip_failures,
        report_md_path=f"{args.output}/phase5d_end_to_end_performance.md",
        report_json_path=f"{args.output}/phase5d_end_to_end_performance.json"
    )

    db = SessionLocal()
    try:
        runner = BenchmarkReliabilityRunner(config=config)
        env_info = ResourceMonitor.get_environment_info()

        print(f"Hardware Environment: {env_info.get('gpu_name')} | CUDA: {env_info.get('cuda_available')}")
        print(f"OS: {env_info.get('os_system')} {env_info.get('os_release')} | Python: {env_info.get('python_version')} | PyTorch: {env_info.get('pytorch_version')}")
        print("-" * 80)

        t_total_start = time.perf_counter()
        durations = {
            "performance_benchmark_seconds": 0.0,
            "multi_image_workload_seconds": 0.0,
            "failure_recovery_seconds": 0.0,
            "total_wall_clock_seconds": 0.0
        }

        repeatability_data: dict = {}
        multi_img_data: dict = {}
        failure_tests: dict = {}

        # 1. Performance Benchmark on Primary Image (quick, repeatability, or full)
        if selected_mode in ("quick", "repeatability", "full"):
            t_bench = time.perf_counter()
            repeatability_data = runner.run_repeatability_benchmark(
                image_path=args.image,
                warmup_runs=warmup_runs,
                measured_runs=measured_runs,
                db=db
            )
            durations["performance_benchmark_seconds"] = round(time.perf_counter() - t_bench, 2)

        # 2. Multi-Image Workload across 10 Real Images (multi-image or full)
        if selected_mode in ("multi-image", "full"):
            t_multi = time.perf_counter()
            multi_img_data = runner.run_multi_image_workload(db=db)
            durations["multi_image_workload_seconds"] = round(time.perf_counter() - t_multi, 2)
        else:
            print(f"Multi-image workload skipped (Mode is {selected_mode.upper()}).")

        # 3. Controlled Failure Recovery Tests (failures or full unless skip_failures)
        if selected_mode == "failures" or (selected_mode == "full" and not args.skip_failures):
            print("\nExecuting Controlled Failure Recovery Tests (10 scenarios)...")
            t_fail = time.perf_counter()
            failure_tests = runner.run_failure_recovery_tests()
            durations["failure_recovery_seconds"] = round(time.perf_counter() - t_fail, 2)
            passed_failures = failure_tests.get("passed_cases", 0)
            total_failures = failure_tests.get("total_cases", 0)
            print(f"Failure Recovery Result: {passed_failures}/{total_failures} scenarios passed safely.")
        else:
            print(f"Failure recovery tests skipped (Mode is {selected_mode.upper()}).")

        durations["total_wall_clock_seconds"] = round(time.perf_counter() - t_total_start, 2)

        # Sample resources & regression comparison
        res_sample = runner.resource_monitor.sample_resources()

        llm_stats = repeatability_data.get("stage_summary", {}).get("I_llm_generation_ms", {})
        current_llm_mean = llm_stats.get("mean", 0.0) if isinstance(llm_stats.get("mean"), (int, float)) else 0.0
        reg_comp = compute_regression_comparison(
            current_mean_ms=current_llm_mean,
            baseline_mean_ms=config.phase_5c_baseline.get("mean_latency_ms", 27262.21)
        )

        # Assemble benchmark payload
        benchmark_payload = {
            "phase": "5D",
            "benchmark_title": "Phase 5D End-to-End Performance and Reliability Benchmark",
            "mode": selected_mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workload_durations_seconds": durations,
            "total_benchmark_duration_seconds": durations["total_wall_clock_seconds"],
            "environment": env_info,
            "resources": res_sample,
            "repeatability_benchmark": repeatability_data,
            "multi_image_benchmark": multi_img_data,
            "failure_recovery_tests": failure_tests,
            "regression_comparison": reg_comp
        }

        # Save Reports
        reporter = BenchmarkReportGenerator(config=config)
        saved_paths = reporter.save_reports(benchmark_payload)

        # Print Console Summary
        det_cons = repeatability_data.get("deterministic_consistency", {})
        tp = repeatability_data.get("throughput", {})
        e2e_stats = repeatability_data.get("stage_summary", {}).get("M_complete_end_to_end_ms", {})
        state_label = repeatability_data.get("execution_state_label", "N/A")

        print("\n" + "=" * 80)
        print("PHASE 5D BENCHMARK RESULTS SUMMARY")
        print("=" * 80)
        print(f"Execution State              : [{state_label}]")
        print(f"Mean End-to-End Latency      : {e2e_stats.get('mean', 'N/A')} ms ({round(e2e_stats.get('mean', 0)/1000, 2) if isinstance(e2e_stats.get('mean'), (int, float)) else 'N/A'} s)")
        print(f"YOLO11n-seg Inference Mean   : {repeatability_data.get('stage_summary', {}).get('C_yolo_inference_ms', {}).get('mean', 'N/A')} ms")
        print(f"Gemma 3 Generation Mean      : {llm_stats.get('mean', 'N/A')} ms")
        if repeatability_data and repeatability_data.get("runs"):
            det_status = f"100% Deterministic = {det_cons.get('all_deterministic_invariants_hold', False)}"
        else:
            det_status = "N/A (Repeatability not executed in this mode)"
        print(f"Deterministic Consistency    : {det_status}")
        print("Workload Durations:")
        print(f"  Performance Benchmark      : {durations.get('performance_benchmark_seconds')} s")
        print(f"  Multi-Image Workload       : {durations.get('multi_image_workload_seconds')} s")
        print(f"  Failure Recovery Suite     : {durations.get('failure_recovery_seconds')} s")
        print(f"  Total Wall-Clock Execution : {durations.get('total_wall_clock_seconds')} s")
        print("-" * 80)
        print("Generated Audit Reports:")
        for k, v in saved_paths.items():
            print(f"  {k:18s}: {v}")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
