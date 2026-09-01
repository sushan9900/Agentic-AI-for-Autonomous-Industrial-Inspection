"""Integration and End-to-End Test Suite for Phase 3C.

Validates the complete real inspection lifecycle:
Vision Model -> Evidence -> Agent Reasoning -> Persistence -> Trace -> Safety Gates -> Failure Modes.
"""

from pathlib import Path
import pytest
from backend.app.agents.inspection_agent import (
    VisionEvidenceInvalidError,
    inspection_decision_agent,
)
from backend.app.database.models.agent_decision import (
    AgentDecisionModel,
    AgentReasoningTraceModel,
)
from backend.app.database.session import SessionLocal
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.schemas import LLMGenerationRequest, LLMGenerationResponse
from backend.app.services.agent import agent_decision_service
from backend.app.services.end_to_end_inspection import EndToEndInspectionService
from vision.schemas.evidence import InspectionStatus, VisionEvidence

REAL_TEST_IMAGE = "data/processed/deepcrack/yolo/images/test/11112.jpg"
REAL_CHECKPOINT = "experiments/vision/deepcrack/baseline/weights/best.pt"
ASSET_ID = "ASSET-PL-01"
COMP_ID = "PIPE-SEG-4021"


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def e2e_service():
    assert Path(REAL_TEST_IMAGE).exists(), f"Image {REAL_TEST_IMAGE} must exist"
    assert Path(REAL_CHECKPOINT).exists(), f"Checkpoint {REAL_CHECKPOINT} must exist"
    return EndToEndInspectionService(model_checkpoint_path=REAL_CHECKPOINT, device="cuda")


def test_1_real_vision_to_evidence_conversion(e2e_service):
    """Test 1: Validates that YOLO inference produces a compliant VisionEvidence v1.0 object."""
    pipeline = e2e_service._get_pipeline()
    evidence = pipeline.run_inspection_evidence(
        image_path=REAL_TEST_IMAGE,
        component_id=COMP_ID,
        inspection_id="insp-p3c-test-01",
        component_type="pipeline"
    )

    assert isinstance(evidence, VisionEvidence)
    assert evidence.schema_version == "1.0"
    assert evidence.status in (InspectionStatus.SUCCESS, InspectionStatus.NO_DETECTIONS)
    assert len(evidence.detections) >= 1
    assert evidence.source_image.sha256_hash is not None
    assert evidence.processing.total_execution_ms > 0.0


def test_2_evidence_to_agent_handoff_and_decision(e2e_service, db_session):
    """Test 2: Validates agent execution on real vision evidence."""
    pipeline = e2e_service._get_pipeline()
    evidence = pipeline.run_inspection_evidence(
        image_path=REAL_TEST_IMAGE,
        component_id=COMP_ID,
        inspection_id="insp-p3c-test-02",
        component_type="pipeline"
    )

    decision = inspection_decision_agent.run_inspection(
        inspection_id=evidence.inspection_id,
        asset_id=ASSET_ID,
        evidence=evidence,
        db=db_session,
        component_id=COMP_ID
    )

    assert decision.decision_id == f"dec-{evidence.inspection_id}-{ASSET_ID}"
    assert decision.operational_decision in (
        "URGENT_ENGINEERING_REVIEW",
        "PRIORITY_MAINTENANCE",
        "PLAN_MAINTENANCE",
        "SCHEDULE_INSPECTION",
        "MONITOR"
    )
    assert decision.risk_assessment["risk_score"] >= 0
    assert len(decision.reasoning_trace) == 11


def test_3_agent_to_persistence(e2e_service, db_session):
    """Test 3: Validates that an autonomous inspection decision and traces persist in PostgreSQL."""
    test_insp_id = "insp-p3c-test-03"
    test_dec_id = f"dec-{test_insp_id}-{ASSET_ID}"

    # Clean up prior
    db_session.query(AgentReasoningTraceModel).filter(AgentReasoningTraceModel.decision_id == test_dec_id).delete()
    db_session.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == test_dec_id).delete()
    db_session.commit()

    decision = e2e_service.run_e2e_inspection(
        image_path=REAL_TEST_IMAGE,
        asset_id=ASSET_ID,
        component_id=COMP_ID,
        inspection_id=test_insp_id,
        db=db_session
    )

    db_rec = db_session.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == decision.decision_id).first()
    assert db_rec is not None
    assert db_rec.decision_id == decision.decision_id
    assert db_rec.operational_decision == decision.operational_decision


def test_4_persistence_to_retrieval(db_session):
    """Test 4: Validates lossless retrieval of persisted decision and structured attributes."""
    test_dec_id = f"dec-insp-p3c-test-03-{ASSET_ID}"
    retrieved = agent_decision_service.get_decision(db=db_session, decision_id=test_dec_id)
    assert retrieved.decision_id == test_dec_id
    assert retrieved.human_review_required is True
    assert retrieved.risk_assessment["risk_score"] >= 0


def test_5_trace_retrieval_and_ordering(db_session):
    """Test 5: Validates that all 11 stages in the trace are correctly ordered."""
    test_dec_id = f"dec-insp-p3c-test-03-{ASSET_ID}"
    traces = agent_decision_service.get_decision_traces(db=db_session, decision_id=test_dec_id)

    assert len(traces) == 11
    expected_stages = [
        "INGEST_EVIDENCE",
        "VALIDATE_EVIDENCE",
        "GET_ASSET_CONTEXT",
        "GET_MAINTENANCE_HISTORY",
        "GET_SEVERITY_THRESHOLDS",
        "CHECK_SIMILAR_INCIDENTS",
        "ASSESS_RISK",
        "FORMULATE_DECISION",
        "GENERATE_WORK_ORDER",
        "FINAL_VALIDATION",
        "HUMAN_REVIEW_REQUIRED"
    ]
    for i, stage in enumerate(expected_stages):
        assert traces[i].step == i + 1
        assert traces[i].stage == stage
        assert traces[i].status == "completed"


def test_6_human_review_safety_gate(e2e_service, db_session):
    """Test 6: Validates that human review is strictly required on all recommendations."""
    decision = e2e_service.run_e2e_inspection(
        image_path=REAL_TEST_IMAGE,
        asset_id=ASSET_ID,
        component_id=COMP_ID,
        inspection_id="insp-p3c-test-06",
        db=db_session
    )
    assert decision.human_review_required is True
    assert decision.work_order is not None
    assert decision.work_order.status == "PENDING_HUMAN_REVIEW"


def test_7_missing_image_failure_handling(e2e_service, db_session):
    """Test 7: Validates clean failure when source image is missing."""
    with pytest.raises(FileNotFoundError):
        e2e_service.run_e2e_inspection(
            image_path="nonexistent/path/to/missing_image.jpg",
            asset_id=ASSET_ID,
            component_id=COMP_ID,
            db=db_session
        )


def test_8_invalid_evidence_failure_handling(db_session):
    """Test 8: Validates rejection of corrupted or invalid evidence."""
    with pytest.raises(VisionEvidenceInvalidError):
        inspection_decision_agent.run_inspection(
            inspection_id="insp-p3c-corrupt",
            asset_id=ASSET_ID,
            evidence={"corrupt": "data"},
            db=db_session
        )


class FailingMockLLMProvider(BaseLLMProvider):
    """Mock provider simulating an offline or erroring LLM."""
    def model_name(self) -> str:
        return "mock-offline-gemma"
    def is_available(self) -> bool:
        return False
    def health_check(self):
        from backend.app.llm.schemas import LLMHealthStatus
        return LLMHealthStatus(status="unhealthy", provider="mock", model="mock-offline-gemma", is_available=False, error_message="Ollama offline")
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        raise ConnectionError("Ollama daemon is unreachable.")


def test_9_ollama_failure_graceful_fallback(e2e_service, db_session):
    """Test 9: Validates graceful deterministic fallback if Ollama fails."""
    from backend.app.agents.inspection_agent import InspectionDecisionAgent
    fallback_agent = InspectionDecisionAgent(llm_provider=FailingMockLLMProvider())

    pipeline = e2e_service._get_pipeline()
    evidence = pipeline.run_inspection_evidence(
        image_path=REAL_TEST_IMAGE,
        component_id=COMP_ID,
        inspection_id="insp-p3c-fallback",
        component_type="pipeline"
    )

    decision = fallback_agent.run_inspection(
        inspection_id=evidence.inspection_id,
        asset_id=ASSET_ID,
        evidence=evidence,
        db=db_session,
        component_id=COMP_ID
    )

    assert decision.operational_decision is not None
    assert decision.work_order is not None
    assert decision.work_order.status == "PENDING_HUMAN_REVIEW"
    assert any("LLM generation/parsing encountered issue" in w for w in decision.warnings)


def test_10_repeatability_of_deterministic_fields(e2e_service, db_session):
    """Test 10: Validates exact stability of deterministic fields across multiple runs."""
    pipeline = e2e_service._get_pipeline()
    ev1 = pipeline.run_inspection_evidence(
        image_path=REAL_TEST_IMAGE,
        component_id=COMP_ID,
        inspection_id="insp-p3c-rep-1",
        component_type="pipeline"
    )
    ev2 = pipeline.run_inspection_evidence(
        image_path=REAL_TEST_IMAGE,
        component_id=COMP_ID,
        inspection_id="insp-p3c-rep-2",
        component_type="pipeline"
    )

    # 1. Perception repeatability
    assert len(ev1.detections) == len(ev2.detections)
    for d1, d2 in zip(ev1.detections, ev2.detections):
        assert d1.defect_type == d2.defect_type
        assert abs(d1.confidence - d2.confidence) < 1e-4
        assert d1.bounding_box.x_norm == d2.bounding_box.x_norm
        assert d1.bounding_box.y_norm == d2.bounding_box.y_norm

    # 2. Decision & Risk repeatability
    dec1 = inspection_decision_agent.run_inspection(
        inspection_id=ev1.inspection_id,
        asset_id=ASSET_ID,
        evidence=ev1,
        db=db_session,
        component_id=COMP_ID
    )
    dec2 = inspection_decision_agent.run_inspection(
        inspection_id=ev2.inspection_id,
        asset_id=ASSET_ID,
        evidence=ev2,
        db=db_session,
        component_id=COMP_ID
    )

    assert dec1.risk_assessment["risk_score"] == dec2.risk_assessment["risk_score"]
    assert dec1.risk_assessment["risk_level"] == dec2.risk_assessment["risk_level"]
    assert dec1.operational_decision == dec2.operational_decision
    assert dec1.human_review_required == dec2.human_review_required
