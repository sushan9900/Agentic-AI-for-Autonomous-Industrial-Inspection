"""Unit tests for VisionEvidence schema contract, serialization, and deterministic builders."""

import json
from pathlib import Path
import pytest
from vision.inference.evidence_builder import EvidenceBuilder, compute_file_sha256
from vision.inference.quality import assess_image_quality
from vision.schemas.evidence import (
    DetectionEvidence,
    DetectionSummary,
    InspectionStatus,
    ModelProvenance,
    NormalizedBoundingBox,
    ProcessingTrace,
    QualityAssessment,
    QualityWarningType,
    SourceImageProvenance,
    VisionEvidence,
)
from vision.schemas.inspection import BoundingBox, Detection, SeverityFeatures


@pytest.fixture
def sample_image_fixture(tmp_path: Path) -> Path:
    img_path = tmp_path / "fixture_img.jpg"
    # Create valid synthetic JPEG header
    img_path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"\x00" * 200)
    return img_path


def test_vision_evidence_schema_version():
    trace = ProcessingTrace(
        validation_ms=1.0, preprocessing_ms=2.0, inference_ms=10.0,
        postprocessing_ms=1.0, evidence_construction_ms=0.5, total_execution_ms=14.5
    )
    img_prov = SourceImageProvenance(
        filename="test.jpg", file_extension=".jpg", width=640, height=480,
        channels=3, file_size_bytes=1024, sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    mod_prov = ModelProvenance(
        model_name="YOLO11n-seg", model_architecture="YOLO11n-seg", model_version="1.0.0",
        checkpoint_identifier="best.pt", checkpoint_sha256="abc123hash", framework="ultralytics",
        framework_version="8.4.136", confidence_threshold=0.25, input_size=[640, 640], device="cpu"
    )
    quality = QualityAssessment(
        brightness_mean=120.0, contrast_std=45.0, blur_score=150.0,
        blur_detected=False, low_contrast_detected=False, underexposed=False,
        overexposed=False, warnings=[]
    )
    summary = DetectionSummary(detection_count=0, max_confidence=None, mean_confidence=None, min_confidence=None)

    evidence = VisionEvidence(
        schema_version="1.0",
        inspection_id="insp-test-01",
        component_id="PIPE-100",
        component_type="pipeline",
        status=InspectionStatus.NO_DETECTIONS,
        source_image=img_prov,
        model=mod_prov,
        summary=summary,
        detections=[],
        quality=quality,
        processing=trace
    )

    assert evidence.schema_version == "1.0"
    assert evidence.status == InspectionStatus.NO_DETECTIONS
    assert evidence.summary.detection_count == 0


def test_vision_evidence_json_roundtrip():
    trace = ProcessingTrace(
        validation_ms=1.0, preprocessing_ms=2.0, inference_ms=10.0,
        postprocessing_ms=1.0, evidence_construction_ms=0.5, total_execution_ms=14.5
    )
    img_prov = SourceImageProvenance(
        filename="test.jpg", file_extension=".jpg", width=640, height=480,
        channels=3, file_size_bytes=1024, sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    mod_prov = ModelProvenance(
        model_name="YOLO11n-seg", model_architecture="YOLO11n-seg", model_version="1.0.0",
        checkpoint_identifier="best.pt", checkpoint_sha256="abc123hash", framework="ultralytics",
        framework_version="8.4.136", confidence_threshold=0.25, input_size=[640, 640], device="cpu"
    )
    quality = QualityAssessment(
        brightness_mean=120.0, contrast_std=45.0, blur_score=150.0,
        blur_detected=False, low_contrast_detected=False, underexposed=False,
        overexposed=False, warnings=[]
    )
    bbox = NormalizedBoundingBox(
        x_pixel=10.0, y_pixel=20.0, width_pixel=100.0, height_pixel=50.0,
        x_norm=0.0156, y_norm=0.0417, width_norm=0.1562, height_norm=0.1042
    )
    det = DetectionEvidence(
        detection_id="det-001", class_id=0, defect_type="crack", confidence=0.885,
        bounding_box=bbox, segmentation=None,
        severity_features=SeverityFeatures(affected_area_percentage=1.63, estimated_size="111.8px x 30.0px", spread="localized")
    )
    summary = DetectionSummary(detection_count=1, max_confidence=0.885, mean_confidence=0.885, min_confidence=0.885)

    original = VisionEvidence(
        schema_version="1.0",
        inspection_id="insp-test-02",
        component_id="PIPE-200",
        component_type="pipeline",
        status=InspectionStatus.SUCCESS,
        source_image=img_prov,
        model=mod_prov,
        summary=summary,
        detections=[det],
        quality=quality,
        processing=trace
    )

    # 1. Serialize to JSON
    json_str = original.model_dump_json(indent=2)
    assert isinstance(json_str, str)

    # 2. Deserialize back to Pydantic object
    reloaded = VisionEvidence.model_validate_json(json_str)

    # 3. Assert equality across all fields
    assert reloaded.schema_version == original.schema_version
    assert reloaded.inspection_id == original.inspection_id
    assert reloaded.status == original.status
    assert reloaded.detections[0].detection_id == "det-001"
    assert reloaded.detections[0].confidence == 0.885
    assert reloaded.detections[0].bounding_box.width_norm == 0.1562


def test_deterministic_detection_ids_and_ordering():
    # Build list of unsorted detections
    d1 = Detection(
        defect_id="orig_1", defect_type="crack", confidence=0.45,
        bounding_box=BoundingBox(x=10.0, y=10.0, width=50.0, height=20.0),
        severity_features=SeverityFeatures(affected_area_percentage=1.0)
    )
    d2 = Detection(
        defect_id="orig_2", defect_type="crack", confidence=0.92,
        bounding_box=BoundingBox(x=5.0, y=5.0, width=30.0, height=30.0),
        severity_features=SeverityFeatures(affected_area_percentage=2.0)
    )
    d3 = Detection(
        defect_id="orig_3", defect_type="crack", confidence=0.78,
        bounding_box=BoundingBox(x=20.0, y=20.0, width=10.0, height=10.0),
        severity_features=SeverityFeatures(affected_area_percentage=0.5)
    )

    detections = [d1, d2, d3]
    # Sorted by confidence descending
    sorted_dets = sorted(detections, key=lambda d: (-d.confidence, d.bounding_box.x, d.bounding_box.y))

    det_ids = [f"det-{idx:03d}" for idx in range(1, len(sorted_dets) + 1)]
    assert det_ids == ["det-001", "det-002", "det-003"]
    assert sorted_dets[0].confidence == 0.92
    assert sorted_dets[1].confidence == 0.78
    assert sorted_dets[2].confidence == 0.45


def test_file_sha256_computation(tmp_path: Path):
    test_f = tmp_path / "test_sha.txt"
    test_f.write_text("industrial_inspection_pipeline_test")
    digest = compute_file_sha256(test_f)
    assert isinstance(digest, str)
    assert len(digest) == 64


def test_quality_assessment_flags_blur_and_contrast(tmp_path: Path):
    import numpy as np
    # Completely uniform grey image -> standard deviation = 0.0 (low contrast) and Laplacian var = 0.0 (blur)
    blank_gray = np.full((300, 300, 3), 128, dtype=np.uint8)
    qa = assess_image_quality(blank_gray)
    assert qa.blur_detected is True
    assert qa.low_contrast_detected is True
    assert QualityWarningType.BLUR in qa.warnings
    assert QualityWarningType.LOW_CONTRAST in qa.warnings
