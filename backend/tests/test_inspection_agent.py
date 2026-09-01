"""Unit tests for InspectionReasoningAgent, Prompt Builder, and Work Order synthesis."""

import json
import pytest
from unittest.mock import MagicMock
from backend.app.agents.inspection_agent import ComponentNotFoundError, InspectionReasoningAgent
from backend.app.agents.reasoning import ReasoningParser, ReasoningParserError
from backend.app.agents.work_order import WorkOrderSynthesizer
from backend.app.database.session import SessionLocal
from backend.app.llm.base import BaseLLMProvider
from backend.app.llm.prompts.inspection_reasoning import InspectionPromptBuilder
from backend.app.llm.schemas import LLMGenerationRequest, LLMGenerationResponse, LLMHealthStatus
from backend.app.schemas.agent_assessment import DraftWorkOrder, InspectionAssessmentResponse
from backend.app.services.context.context_service import context_service
from backend.app.services.decision.decision_service import decision_service
from vision.schemas.evidence import (
    DetectionEvidence,
    DetectionSummary,
    InspectionStatus,
    ModelProvenance,
    NormalizedBoundingBox,
    ProcessingTrace,
    QualityAssessment,
    SourceImageProvenance,
    VisionEvidence,
)
from vision.schemas.inspection import SeverityFeatures


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock LLM provider for unit tests."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_prompt = None

    def model_name(self) -> str:
        return "mock-gemma3:latest"

    def health_check(self) -> LLMHealthStatus:
        return LLMHealthStatus(provider="mock", model="mock-gemma3", available=True)

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResponse:
        self.last_prompt = request.prompt
        return LLMGenerationResponse(
            text=self.response_text,
            model="mock-gemma3:latest",
            duration_ms=45.2,
            prompt_tokens=150,
            completion_tokens=80
        )


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_vision_evidence() -> VisionEvidence:
    trace = ProcessingTrace(
        validation_ms=0.5, preprocessing_ms=1.0, inference_ms=50.0,
        postprocessing_ms=0.5, evidence_construction_ms=0.2, total_execution_ms=52.2
    )
    img_prov = SourceImageProvenance(
        filename="11112.jpg", file_extension=".jpg", width=640, height=480,
        channels=3, file_size_bytes=45000, sha256_hash="44e62c6410a898b496e245ac28f3f1604c31acb04cad4e5b0551738f40a78313"
    )
    mod_prov = ModelProvenance(
        model_name="YOLO11n-seg", model_architecture="YOLO11n-seg", model_version="1.0.0",
        checkpoint_identifier="best.pt", checkpoint_sha256="f9a4ab02b705aa9c", framework="ultralytics",
        framework_version="8.4.136", confidence_threshold=0.25, input_size=[640, 640], device="0"
    )
    quality = QualityAssessment(
        brightness_mean=120.0, contrast_std=45.0, blur_score=150.0,
        blur_detected=False, low_contrast_detected=False, underexposed=False,
        overexposed=False, warnings=[]
    )
    bbox = NormalizedBoundingBox(
        x_pixel=10.0, y_pixel=10.0, width_pixel=50.0, height_pixel=30.0,
        x_norm=0.0156, y_norm=0.0208, width_norm=0.0781, height_norm=0.0625
    )
    det = DetectionEvidence(
        detection_id="det-001", class_id=0, defect_type="crack", confidence=0.88,
        bounding_box=bbox,
        severity_features=SeverityFeatures(affected_area_percentage=3.5, crack_length_pixels=240.0)
    )
    summary = DetectionSummary(detection_count=1, max_confidence=0.88, mean_confidence=0.88, min_confidence=0.88)

    return VisionEvidence(
        schema_version="1.0",
        inspection_id="insp-unit-test-001",
        component_id="PIPE-SEG-4021",
        component_type="PIPE_SEGMENT",
        status=InspectionStatus.SUCCESS,
        source_image=img_prov,
        model=mod_prov,
        summary=summary,
        detections=[det],
        quality=quality,
        processing=trace
    )


def test_prompt_builder_structure(sample_vision_evidence, db_session):
    context = context_service.get_component_context(db_session, "PIPE-SEG-4021")
    decision = decision_service.evaluate_inspection(sample_vision_evidence)

    prompt = InspectionPromptBuilder.build_prompt(
        evidence=sample_vision_evidence,
        decision=decision,
        context=context
    )

    assert "CURRENT INSPECTION EVIDENCE" in prompt
    assert "DETERMINISTIC DECISION RULES" in prompt
    assert "ASSET & COMPONENT SPECIFICATIONS" in prompt
    assert "HISTORICAL MAINTENANCE & SERVICE LOGS" in prompt
    assert "PRIOR INSPECTION RECORDS" in prompt
    assert "DATA PROVENANCE: DEVELOPMENT_SYNTHETIC" in prompt
    assert "REQUIRED JSON OUTPUT FORMAT" in prompt


def test_work_order_synthesizer_pending_status():
    dwo = WorkOrderSynthesizer.create_draft(
        draft_id="wo-123",
        component_id="PIPE-SEG-4021",
        inspection_reference="insp-123",
        priority="HIGH",
        recommended_action="Execute ultrasonic verification",
        justification="Observed crack indication",
        required_inspection="Ultrasonic NDE",
        suggested_team="Pipeline Integrity Team"
    )
    assert isinstance(dwo, DraftWorkOrder)
    assert dwo.approval_status == "PENDING_HUMAN_REVIEW"
    assert dwo.priority == "HIGH"


def test_reasoning_parser_rejects_malformed_json(sample_vision_evidence, db_session):
    context = context_service.get_component_context(db_session, "PIPE-SEG-4021")
    decision = decision_service.evaluate_inspection(sample_vision_evidence)

    bad_text = "This is not JSON text."
    with pytest.raises(ReasoningParserError):
        ReasoningParser.parse_llm_response(
            raw_text=bad_text,
            assessment_id="assess-1",
            draft_id="draft-1",
            evidence=sample_vision_evidence,
            decision=decision,
            context=context,
            model_provenance={}
        )


def test_inspection_reasoning_agent_end_to_end(sample_vision_evidence, db_session):
    mock_llm_json = json.dumps({
        "summary": "Visual evidence detected localized crack on pipe segment.",
        "historical_context_summary": "Segment previously serviced with protective epoxy coating in 2024.",
        "reasoning": "Observed surface crack propagation may breach exterior epoxy barrier.",
        "risk_factors": ["Coating degradation", "Potential localized fatigue"],
        "recommended_actions": ["Conduct ultrasonic thickness survey", "Inspect epoxy seal"],
        "confidence": "HIGH",
        "uncertainty": "Surface crack depth cannot be determined from monocular optical inspection alone.",
        "draft_work_order": {
            "priority": "HIGH",
            "recommended_action": "Schedule specialized ultrasonic NDE verification within 48 hours.",
            "justification": "Surface crack indication in upper quadrant.",
            "required_inspection": "Ultrasonic Shear Wave NDE",
            "suggested_team": "Pipeline Integrity Unit",
            "estimated_downtime_hours": 3.0,
            "estimated_cost": 1800.0,
            "supporting_evidence": ["det-001 (crack length 240px)"],
            "historical_support": ["MAINT-2024-0891 coating baseline"]
        }
    })

    mock_provider = MockLLMProvider(mock_llm_json)
    agent = InspectionReasoningAgent(llm_provider=mock_provider)

    res = agent.assess_inspection(
        vision_evidence=sample_vision_evidence,
        component_id="PIPE-SEG-4021",
        db=db_session
    )

    assert isinstance(res, InspectionAssessmentResponse)
    assert res.assessment.schema_version == "1.0"
    assert res.assessment.human_review_required is True
    assert res.draft_work_order.approval_status == "PENDING_HUMAN_REVIEW"
    assert res.reasoning_trace.provider == "ollama"
    assert res.reasoning_trace.human_review_status == "PENDING_HUMAN_REVIEW"


def test_inspection_reasoning_agent_missing_component(sample_vision_evidence, db_session):
    mock_provider = MockLLMProvider('{}')
    agent = InspectionReasoningAgent(llm_provider=mock_provider)

    with pytest.raises(ComponentNotFoundError):
        agent.assess_inspection(
            vision_evidence=sample_vision_evidence,
            component_id="NON-EXISTENT-COMPONENT",
            db=db_session
        )
