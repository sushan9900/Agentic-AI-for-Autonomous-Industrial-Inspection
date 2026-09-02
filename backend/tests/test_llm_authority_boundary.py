"""Unit tests strictly enforcing the LLM authority boundary (Phase 5B)."""

import json
from pathlib import Path
import pytest
from backend.app.agents.inspection_agent import InspectionDecisionAgent
from backend.app.database.session import SessionLocal
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.schemas import LLMGenerationRequest, LLMGenerationResponse, LLMHealthStatus

EVIDENCE_FILE = Path("experiments/vision/deepcrack/inference/evidence/11112.evidence.json")


class MockOverrideLLMProvider(BaseLLMProvider):
    """Mock LLM provider that attempts to hallucinate different actions/scores."""
    def __init__(self, hallucinated_action: str = "MONITOR", hallucinated_score: int = 10, malformed: bool = False):
        self.hallucinated_action = hallucinated_action
        self.hallucinated_score = hallucinated_score
        self.malformed = malformed

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        if self.malformed:
            return LLMGenerationResponse(
                text="<<< NOT JSON >>>",
                model="mock-llm",
                duration_ms=10.0
            )

        payload = {
            "recommended_action": f"LLM recommends: {self.hallucinated_action}",
            "justification": f"LLM hallucinated justification with score {self.hallucinated_score}",
            "required_inspection_methods": ["Visual Inspection"],
            "safety_notes": ["PPE required"],
            "estimated_cost": 100.0,
            "estimated_downtime_hours": 2.0,
            "cost_notes": "Estimated"
        }
        return LLMGenerationResponse(
            text=json.dumps(payload),
            model="mock-llm",
            duration_ms=15.0
        )

    def health_check(self) -> LLMHealthStatus:
        return LLMHealthStatus(available=True, model="mock-llm", provider="mock")

    def model_name(self) -> str:
        return "mock-llm"


class MockFailingLLMProvider(BaseLLMProvider):
    """Mock LLM provider that throws exceptions or timeouts."""
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        raise RuntimeError("Ollama service timeout or network disconnection.")

    def health_check(self) -> LLMHealthStatus:
        return LLMHealthStatus(available=False, model="mock-llm", provider="mock", details="Unavailable")

    def model_name(self) -> str:
        return "mock-llm"


@pytest.fixture
def test_evidence():
    with open(EVIDENCE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_case_a_llm_claims_lower_risk_action(test_evidence):
    """Case A: LLM claims lower action (MONITOR), but deterministic engine maintains URGENT_ENGINEERING_REVIEW."""
    agent = InspectionDecisionAgent(llm_provider=MockOverrideLLMProvider(hallucinated_action="MONITOR", hallucinated_score=10))
    db = SessionLocal()
    try:
        decision = agent.run_inspection(
            inspection_id="insp-boundary-01",
            asset_id="ASSET-PL-01",
            evidence=test_evidence,
            db=db
        )
        assert decision.operational_decision == "URGENT_ENGINEERING_REVIEW"
        assert decision.risk_assessment["risk_score"] >= 75
        assert decision.risk_assessment["risk_level"] == "CRITICAL"
        assert decision.human_review_required is True
    finally:
        db.close()


def test_case_b_llm_claims_higher_risk_action(test_evidence):
    """Case B: LLM claims higher action on low risk evidence, but deterministic engine maintains MONITOR."""
    low_evidence = dict(test_evidence)
    low_evidence["detections"] = []
    low_evidence["summary"] = {
        "detection_count": 0,
        "max_confidence": 0.0,
        "mean_confidence": 0.0,
        "min_confidence": 0.0
    }

    agent = InspectionDecisionAgent(llm_provider=MockOverrideLLMProvider(hallucinated_action="URGENT_SHUTDOWN", hallucinated_score=100))
    db = SessionLocal()
    try:
        decision = agent.run_inspection(
            inspection_id="insp-boundary-02",
            asset_id="ASSET-PL-01",
            evidence=low_evidence,
            db=db
        )
        # Deterministic engine evaluates to PRIORITY_MAINTENANCE due to asset history/recurrence,
        # and strictly rejects the LLM's hallucinated action 'URGENT_SHUTDOWN' and score 100.
        assert decision.operational_decision == "PRIORITY_MAINTENANCE"
        assert decision.operational_decision != "URGENT_SHUTDOWN"
        assert decision.risk_assessment["risk_score"] < 75
        assert decision.risk_assessment["risk_level"] != "CRITICAL"
    finally:
        db.close()


def test_case_c_llm_malformed_json_output(test_evidence):
    """Case C: LLM produces invalid/malformed JSON string, fallback draft work-order generated safely."""
    agent = InspectionDecisionAgent(llm_provider=MockOverrideLLMProvider(malformed=True))
    db = SessionLocal()
    try:
        decision = agent.run_inspection(
            inspection_id="insp-boundary-03",
            asset_id="ASSET-PL-01",
            evidence=test_evidence,
            db=db
        )
        assert decision.operational_decision == "URGENT_ENGINEERING_REVIEW"
        assert decision.work_order is not None
        assert decision.work_order.priority == "CRITICAL"
        assert any("fallback" in w.lower() or "llm" in w.lower() for w in decision.warnings)
    finally:
        db.close()


def test_case_d_llm_offline_or_unavailable(test_evidence):
    """Case D: LLM provider throws error/timeout, system falls back gracefully with audit warning."""
    agent = InspectionDecisionAgent(llm_provider=MockFailingLLMProvider())
    db = SessionLocal()
    try:
        decision = agent.run_inspection(
            inspection_id="insp-boundary-04",
            asset_id="ASSET-PL-01",
            evidence=test_evidence,
            db=db
        )
        assert decision.operational_decision == "URGENT_ENGINEERING_REVIEW"
        assert decision.work_order is not None
        assert any("fallback" in w.lower() or "llm" in w.lower() for w in decision.warnings)
    finally:
        db.close()
