"""API integration tests for /api/v1/inspection/assessment and /api/v1/llm/health."""

import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.llm.schemas import LLMGenerationResponse
from backend.app.main import app
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

client = TestClient(app)


def get_assessment_payload(component_id: str = "PIPE-SEG-4021") -> dict:
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

    evidence = VisionEvidence(
        schema_version="1.0",
        inspection_id="insp-api-assess-01",
        component_id=component_id,
        component_type="PIPE_SEGMENT",
        status=InspectionStatus.SUCCESS,
        source_image=img_prov,
        model=mod_prov,
        summary=summary,
        detections=[det],
        quality=quality,
        processing=trace
    )

    return {
        "component_id": component_id,
        "vision_evidence": evidence.model_dump(mode="json")
    }


def test_get_llm_health_endpoint():
    response = client.get("/api/v1/llm/health")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "ollama"
    assert "model" in data


def test_post_inspection_assessment_endpoint_success():
    payload = get_assessment_payload("PIPE-SEG-4021")
    
    mock_llm_json = json.dumps({
        "summary": "Pipe segment 4021 inspection identified surface crack.",
        "historical_context_summary": "Prior coating maintenance in 2024.",
        "reasoning": "Crack requires non-destructive examination.",
        "risk_factors": ["Pressure fatigue"],
        "recommended_actions": ["Ultrasonic survey"],
        "confidence": "HIGH",
        "uncertainty": "Visual perception only.",
        "draft_work_order": {
            "priority": "HIGH",
            "recommended_action": "Execute ultrasonic shear wave test.",
            "justification": "Surface crack indication.",
            "required_inspection": "Ultrasonic NDE",
            "suggested_team": "Pipeline Inspection Team",
            "estimated_downtime_hours": 2.0,
            "estimated_cost": 1500.0,
            "supporting_evidence": ["det-001"],
            "historical_support": ["MAINT-2024-0891"]
        }
    })

    with patch("backend.app.llm.ollama.OllamaProvider.generate", return_value=LLMGenerationResponse(
        text=mock_llm_json, model="gemma3:latest", duration_ms=50.0
    )):
        response = client.post("/api/v1/inspection/assessment", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "assessment" in data
        assert "draft_work_order" in data
        assert "reasoning_trace" in data
        assert data["assessment"]["human_review_required"] is True
        assert data["draft_work_order"]["approval_status"] == "PENDING_HUMAN_REVIEW"


def test_post_inspection_assessment_component_not_found():
    payload = get_assessment_payload("NON-EXISTENT-COMP-999")
    response = client.post("/api/v1/inspection/assessment", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
