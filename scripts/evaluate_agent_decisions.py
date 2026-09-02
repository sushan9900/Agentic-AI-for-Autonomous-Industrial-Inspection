"""Executable CLI script to run comprehensive Agent Decision & Safety Evaluation (Phase 5B)."""

import argparse
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.database.session import SessionLocal
from backend.app.evaluation.agent_evaluator import AgentDecisionEvaluator
from backend.app.evaluation.report import AgentEvaluationReportGenerator


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Agent Decision Policy and Safety Invariants.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/vision/deepcrack/reports",
        help="Directory to save output evaluation reports."
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=25,
        help="Number of repeatability test cycles (default: 25)."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 75)
    print("PHASE 5B: AGENT DECISION POLICY & SAFETY CONSISTENCY EVALUATION")
    print("=" * 75)
    print(f"Output Reports Dir : {args.output_dir}")
    print(f"Repeatability Cycles: {args.cycles}")
    print("-" * 75)

    db = SessionLocal()
    try:
        evaluator = AgentDecisionEvaluator(db=db)
        print("Executing decision cases, risk validation, safety invariants, and real evidence...")
        t0 = time.perf_counter()
        eval_result = evaluator.evaluate_all()
        duration = time.perf_counter() - t0

        # Save reports
        report_gen = AgentEvaluationReportGenerator(output_dir=args.output_dir)
        saved_paths = report_gen.save_all(eval_result)

        dpe = eval_result.get("decision_policy_evaluation", {})
        safety = eval_result.get("safety_invariants", {})
        mono = eval_result.get("monotonicity_validation", {})
        repeat = eval_result.get("repeatability_validation", {})
        real = eval_result.get("real_evidence_validation", {})

        print("\n" + "=" * 75)
        print("AGENT DECISION EVALUATION RESULTS SUMMARY")
        print("=" * 75)
        print(f"Decision Cases Evaluated    : {dpe.get('total_cases')}")
        print(f"Decision Cases Matched      : {dpe.get('matched_cases')} ({dpe.get('accuracy', 0.0)*100:.1f}%)")
        print("-" * 75)
        print(f"Safety Invariants Passed    : {safety.get('passed_invariants')}/{safety.get('total_invariants')} (All Passed: {safety.get('all_invariants_passed')})")
        print(f"Monotonic Risk Checks Passed: {mono.get('all_monotonic_checks_passed')}")
        print(f"Repeatability Stability     : {repeat.get('num_cycles')} cycles (100% Deterministic: {repeat.get('is_100_percent_repeatable')})")
        print("-" * 75)
        print(f"Real Validation (11112.jpg) : {real.get('detections_count')} detections | Risk={real.get('risk_score')}/100 ({real.get('risk_level')}) | Action={real.get('operational_decision')}")
        print(f"Real Validation Status      : {'PASSED' if real.get('passed') else 'FAILED'}")
        print(f"Total Evaluation Duration   : {duration:.2f}s")
        print("=" * 75)
        print("\nGenerated Reports:")
        for k, v in saved_paths.items():
            print(f"  {k:22s}: {v}")
        print("=" * 75)

    finally:
        db.close()


if __name__ == "__main__":
    main()
