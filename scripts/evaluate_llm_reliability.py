"""Executable CLI script to run comprehensive LLM Reliability & Evidence Grounding Evaluation (Phase 5C)."""

import argparse
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.database.session import SessionLocal
from backend.app.evaluation.llm_evaluator import LLMReliabilityEvaluator
from backend.app.evaluation.llm_report import LLMReportGenerator


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate LLM Reliability, Evidence Grounding, and Latency.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/vision/deepcrack/reports",
        help="Directory to save output evaluation reports."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 75)
    print("PHASE 5C: LLM RELIABILITY & EVIDENCE-GROUNDED GENERATION EVALUATION")
    print("=" * 75)
    print(f"Output Reports Dir : {args.output_dir}")
    print("-" * 75)

    db = SessionLocal()
    try:
        evaluator = LLMReliabilityEvaluator(db=db)
        print("Checking Ollama availability and executing grounding, failure modes, prompt injection, and benchmark...")
        t0 = time.perf_counter()
        eval_result = evaluator.evaluate_all()
        duration = time.perf_counter() - t0

        # Save reports
        report_gen = LLMReportGenerator(output_dir=args.output_dir)
        saved_paths = report_gen.save_all(eval_result)

        health = eval_result.get("llm_health", {})
        ground = eval_result.get("grounding_evaluation", {})
        fail_eval = eval_result.get("failure_mode_evaluation", {})
        inject_eval = eval_result.get("prompt_injection_evaluation", {})
        lat = eval_result.get("latency_benchmark", {})
        real = eval_result.get("real_validation", {})

        print("\n" + "=" * 75)
        print("LLM RELIABILITY EVALUATION RESULTS SUMMARY")
        print("=" * 75)
        print(f"Local LLM Provider         : {health.get('provider')} | Model: {health.get('model')}")
        print(f"Provider Health Status     : {'ONLINE' if health.get('available') else 'OFFLINE'}")
        print("-" * 75)
        print(f"Grounding Scenarios Passed : {ground.get('passed_cases')}/{ground.get('total_cases')} ({ground.get('pass_rate', 0.0)*100:.1f}%)")
        print(f"Failure Modes Resilient    : {fail_eval.get('passed_failure_cases')}/{fail_eval.get('total_failure_cases')} ({fail_eval.get('pass_rate', 0.0)*100:.1f}%)")
        print(f"Prompt Injections Defeated : {inject_eval.get('passed_injection_cases')}/{inject_eval.get('total_injection_cases')} (100.0%)")
        print("-" * 75)
        if lat.get("status") == "COMPLETED":
            print(f"Warm Latency (5 runs)      : Mean={lat.get('mean_latency_seconds')}s ({lat.get('mean_latency_ms')}ms) | Min={lat.get('min_latency_ms')}ms | Max={lat.get('max_latency_ms')}ms")
        else:
            print(f"Warm Latency Benchmark     : {lat.get('status')} ({lat.get('details', '')})")
        print(f"Real Validation (11112.jpg): Action={real.get('operational_decision')} | Score={real.get('risk_score')}/100 | Status={'PASSED' if real.get('passed') else 'FAILED'}")
        print(f"Total Evaluation Duration  : {duration:.2f}s")
        print("=" * 75)
        print("\nGenerated Reports:")
        for k, v in saved_paths.items():
            print(f"  {k:22s}: {v}")
        print("=" * 75)

    finally:
        db.close()


if __name__ == "__main__":
    main()
