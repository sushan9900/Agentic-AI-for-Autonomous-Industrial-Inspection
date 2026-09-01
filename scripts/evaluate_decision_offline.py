"""Offline decision runner: processes a real VisionEvidence artifact and outputs an authoritative InspectionDecision."""

import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.decision.decision_service import decision_service
from vision.schemas.evidence import VisionEvidence


def evaluate_artifact(evidence_path: Path):
    print(f"Loading real VisionEvidence artifact from: {evidence_path}")
    with open(evidence_path, "r", encoding="utf-8") as f:
        evidence_data = json.load(f)

    # Validate against VisionEvidence contract
    evidence = VisionEvidence.model_validate(evidence_data)

    print(f"Processing evidence through Deterministic Decision Engine (Phase 2A)...")
    decision = decision_service.evaluate_inspection(evidence)

    print("\n================== INSPECTION DECISION =================")
    print(decision.model_dump_json(indent=2))
    print("========================================================")

    out_path = Path("experiments/vision/deepcrack/reports/real_decision_example.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(decision.model_dump_json(indent=2))

    print(f"\n[OK] Decision artifact saved to: {out_path}")
    return decision


if __name__ == "__main__":
    evidence_file = Path("experiments/vision/deepcrack/inference/evidence/11112.evidence.json")
    if not evidence_file.exists():
        evidence_files = list(Path("experiments/vision/deepcrack/inference/evidence").glob("*.json"))
        if evidence_files:
            evidence_file = evidence_files[0]
        else:
            print("Error: No evidence files found.", file=sys.stderr)
            sys.exit(1)

    evaluate_artifact(evidence_file)
