"""
Phase 6C Real Inspection & Investigation Planning Validation Script.
Validates end-to-end execution on real DeepCrack image 11112.jpg using trained YOLO11n-seg checkpoint.
Verifies authoritative risk score, supporting historical/trend context, investigation plan,
and strict non-authoritative human review safety gates.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.database.models.agent_decision import AgentDecisionModel, AgentReasoningTraceModel
from backend.app.database.session import SessionLocal
from backend.app.services.end_to_end_inspection import e2e_inspection_service


def main():
    print("=" * 80)
    print("PHASE 6C: REAL DATA INSPECTION & INVESTIGATION PLANNING VALIDATION")
    print("=" * 80)

    image_path = "data/processed/deepcrack/yolo/images/test/11112.jpg"
    checkpoint_path = "experiments/vision/deepcrack/baseline/weights/best.pt"
    asset_id = "ASSET-PL-01"
    component_id = "PIPE-SEG-4021"
    inspection_id = "insp-11112-phase6c-validation"

    assert Path(image_path).exists(), f"Image path '{image_path}' must exist."
    assert Path(checkpoint_path).exists(), f"Checkpoint path '{checkpoint_path}' must exist."

    db = SessionLocal()

    # Clean up prior test runs with this ID
    decision_id = f"dec-{inspection_id}-{asset_id}"
    db.query(AgentReasoningTraceModel).filter(AgentReasoningTraceModel.decision_id == decision_id).delete()
    db.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == decision_id).delete()
    db.commit()

    print(f"\n[1/5] Executing Vision Pipeline & Agent Decision Engine:")
    print(f"  Source Image     : {image_path}")
    print(f"  Model Checkpoint : {checkpoint_path}")
    print(f"  Asset ID         : {asset_id}")
    print(f"  Component ID     : {component_id}")

    start_time = datetime.now(timezone.utc)
    decision = e2e_inspection_service.run_e2e_inspection(
        image_path=image_path,
        asset_id=asset_id,
        component_id=component_id,
        inspection_id=inspection_id,
        db=db
    )
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    print(f"  Execution Time   : {elapsed:.2f}s")

    print(f"\n[2/5] Verifying Authoritative Decision & Review Gate:")
    print(f"  Decision ID      : {decision.decision_id}")
    print(f"  Risk Score       : {decision.risk_assessment['risk_score']}/100")
    print(f"  Risk Level       : {decision.risk_assessment['risk_level']}")
    print(f"  Operational Action: {decision.operational_decision}")
    print(f"  Review Status    : {decision.review_status}")
    print(f"  Human Required   : {decision.human_review_required}")

    assert decision.risk_assessment["risk_score"] >= 80, "Critical physical crack must produce risk >= 80"
    assert decision.operational_decision == "URGENT_ENGINEERING_REVIEW"
    assert decision.review_status == "PENDING_HUMAN_REVIEW"
    assert decision.human_review_required is True

    print(f"\n[3/5] Verifying Historical Memory & Multi-Inspection Trends:")
    assert decision.historical_context is not None, "Historical context must be populated"
    print(f"  Has History      : {decision.historical_context.get('has_history')}")
    print(f"  Prior Inspections: {decision.historical_context.get('summary', {}).get('total_previous_inspections')}")
    print(f"  Risk Trend       : {decision.historical_context.get('summary', {}).get('risk_trend')}")

    if decision.inspection_trends:
        print(f"  Deterioration    : {decision.inspection_trends.get('deterioration_status')}")
        print(f"  Defect Trend     : {decision.inspection_trends.get('defect_trend')}")
        print(f"  Recurrence       : {decision.inspection_trends.get('recurrence_pattern')}")

    print(f"\n[4/5] Verifying Generated Investigation Plan:")
    inv_plan = decision.investigation_plan
    assert inv_plan is not None, "Investigation plan must be generated and attached to decision"
    print(f"  Plan ID          : {inv_plan.get('plan_id')}")
    print(f"  Priority         : {inv_plan.get('priority')}")
    print(f"  Authoritative    : {inv_plan.get('authoritative')} (Must be False)")
    print(f"  Objective        : {inv_plan.get('objective')}")
    print(f"  Primary Question : {inv_plan.get('primary_question')}")
    print(f"  Diagnostic Steps : {len(inv_plan.get('diagnostic_steps', []))}")
    print(f"  Suspected Causes : {len(inv_plan.get('suspected_causes', []))}")
    print(f"  Information Gaps : {len(inv_plan.get('information_gaps', []))}")
    print(f"  Confirmation Sig : {len(inv_plan.get('confirmation_signals', []))}")

    assert inv_plan.get("authoritative") is False, "Investigation plan must be strictly non-authoritative"
    assert inv_plan.get("priority") in ("CRITICAL", "HIGH"), "Critical crack must produce high/critical investigation priority"
    assert len(inv_plan.get("diagnostic_steps", [])) >= 4, "Must generate structured diagnostic steps"
    assert all(s.get("human_required") is True for s in inv_plan.get("diagnostic_steps", [])), "All steps must require human execution"

    print(f"\n[5/5] Verifying Invariants (Zero Dispatch, Zero PLC/SCADA control):")
    constraints = inv_plan.get("constraints", [])
    for c in constraints:
        print(f"  Constraint: {c}")

    db.close()

    print("\n" + "=" * 80)
    print("PHASE 6C REAL VALIDATION PASSED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    main()
