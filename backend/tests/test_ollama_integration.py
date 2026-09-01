"""Real integration test executing local Ollama inference with gemma3:latest (Phase 2C)."""

import json
from pathlib import Path
import pytest
from backend.app.agents.inspection_agent import InspectionReasoningAgent
from backend.app.database.session import SessionLocal
from backend.app.llm.ollama import OllamaProvider
from backend.app.schemas.agent_assessment import InspectionAssessmentResponse
from vision.schemas.evidence import VisionEvidence


@pytest.mark.integration
def test_real_ollama_inspection_reasoning():
    """Executes a single live agentic assessment test using local Ollama if available."""
    provider = OllamaProvider()
    health = provider.health_check()
    if not health.available:
        pytest.skip(f"Local Ollama server or model not available: {health.details}")

    # Load a real VisionEvidence artifact from Phase 1
    evidence_path = Path("experiments/vision/deepcrack/inference/evidence/11112.evidence.json")
    if not evidence_path.exists():
        pytest.skip("Sample VisionEvidence artifact not found.")

    with open(evidence_path, "r", encoding="utf-8") as f:
        evidence_dict = json.load(f)
    evidence = VisionEvidence.model_validate(evidence_dict)

    db = SessionLocal()
    try:
        agent = InspectionReasoningAgent(llm_provider=provider)
        response = agent.assess_inspection(
            vision_evidence=evidence,
            component_id="PIPE-SEG-4021",
            db=db
        )

        assert isinstance(response, InspectionAssessmentResponse)
        assert response.assessment.schema_version == "1.0"
        assert response.assessment.human_review_required is True
        assert response.draft_work_order.approval_status == "PENDING_HUMAN_REVIEW"
        assert len(response.assessment.summary) > 0
        assert len(response.draft_work_order.recommended_action) > 0
        assert response.reasoning_trace.provider == "ollama"

        # Save assessment artifact for inspection
        out_file = Path("experiments/vision/deepcrack/reports/real_agent_assessment_example.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(response.model_dump_json(indent=2))

    finally:
        db.close()
