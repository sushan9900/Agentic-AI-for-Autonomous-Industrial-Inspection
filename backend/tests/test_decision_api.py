"""API endpoint tests for inspection decision evaluation (Phase 2A)."""

from fastapi.testclient import TestClient
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


def get_valid_evidence_dict() -> dict:
    trace = ProcessingTrace(
        validation_ms=0.5, preprocessing_ms=1.0, inference_ms=50.0,
        postprocessing_ms=0.5, evidence_construction_ms=0.2, total_execution_ms=52.2
    )
    img_prov = SourceImageProvenance(
        filename="test_api_sample.jpg", file_extension=".jpg", width=640, height=480,
        channels=3, file_size_bytes=45000, sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    mod_prov = ModelProvenance(
        model_name="YOLO11n-seg", model_architecture="YOLO11n-seg", model_version="1.0.0",
        checkpoint_identifier="best.pt", checkpoint_sha256="abc123def456", framework="ultralytics",
        framework_version="8.4.136", confidence_threshold=0.25, input_size=[640, 640], device="cpu"
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
        detection_id="det-001", class_id=0, defect_type="crack", confidence=0.82,
        bounding_box=bbox,
        severity_features=SeverityFeatures(affected_area_percentage=1.5, crack_length_pixels=120.0)
    )
    summary = DetectionSummary(detection_count=1, max_confidence=0.82, mean_confidence=0.82, min_confidence=0.82)

    evidence = VisionEvidence(
        schema_version="1.0",
        inspection_id="insp-api-test-01",
        component_id="PIPE-VALVE-501",
        component_type="pipeline",
        status=InspectionStatus.SUCCESS,
        source_image=img_prov,
        model=mod_prov,
        summary=summary,
        detections=[det],
        quality=quality,
        processing=trace
    )
    return evidence.model_dump(mode="json")


def test_post_inspection_decision_valid():
    payload = get_valid_evidence_dict()
    response = client.post("/api/v1/inspection/decision", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == "1.0"
    assert data["inspection_id"] == "insp-api-test-01"
    assert "priority" in data
    assert "confidence" in data
    assert len(data["rule_evaluations"]) == 7
    assert len(data["decision_trace"]) == 4


def test_post_inspection_decision_invalid_payload():
    bad_payload = {"invalid_key": "some_data"}
    response = client.post("/api/v1/inspection/decision", json=bad_payload)
    assert response.status_code == 422


def test_health_endpoint_still_healthy():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint_still_works():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
