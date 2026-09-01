import pytest
from pydantic import ValidationError

from vision.config.settings import VisionSettings
from vision.inference.pipeline import InferencePipeline
from vision.models.base import ModelNotConfiguredError
from vision.preprocessing.pipeline import ImagePreprocessor, InvalidImageInputError
from vision.schemas.inspection import (
    BoundingBox,
    Detection,
    InspectionResult,
    ProcessingMetadata,
    SeverityFeatures,
)


def test_valid_bounding_box():
    """Test valid BoundingBox instantiation."""
    bbox = BoundingBox(x=10.5, y=20.0, width=100.0, height=50.0)
    assert bbox.x == 10.5
    assert bbox.y == 20.0
    assert bbox.width == 100.0
    assert bbox.height == 50.0


def test_invalid_bounding_box_negative_values():
    """Test rejection of negative bounding box coordinates."""
    with pytest.raises(ValidationError):
        BoundingBox(x=-1.0, y=0.0, width=50.0, height=50.0)


def test_valid_detection():
    """Test valid Detection record with optional severity features."""
    bbox = BoundingBox(x=0.0, y=0.0, width=200.0, height=150.0)
    severity = SeverityFeatures(
        affected_area_percentage=15.5,
        location_type="pipe_weld",
        estimated_size="20cm x 15cm",
        spread="circumferential",
        visual_severity="moderate"
    )
    detection = Detection(
        defect_id="def-001",
        defect_type="corrosion",
        confidence=0.88,
        bounding_box=bbox,
        severity_features=severity,
    )
    assert detection.defect_id == "def-001"
    assert detection.defect_type == "corrosion"
    assert detection.confidence == 0.88
    assert detection.severity_features.visual_severity == "moderate"


def test_detection_confidence_boundaries():
    """Test valid boundary confidence values (0.0 and 1.0)."""
    bbox = BoundingBox(x=0.0, y=0.0, width=10.0, height=10.0)
    
    d_min = Detection(defect_id="d1", defect_type="crack", confidence=0.0, bounding_box=bbox)
    assert d_min.confidence == 0.0

    d_max = Detection(defect_id="d2", defect_type="crack", confidence=1.0, bounding_box=bbox)
    assert d_max.confidence == 1.0


def test_invalid_detection_confidence_rejection():
    """Test that confidence < 0.0 or > 1.0 is rejected."""
    bbox = BoundingBox(x=0.0, y=0.0, width=10.0, height=10.0)
    
    with pytest.raises(ValidationError):
        Detection(defect_id="d1", defect_type="crack", confidence=-0.1, bounding_box=bbox)

    with pytest.raises(ValidationError):
        Detection(defect_id="d2", defect_type="crack", confidence=1.05, bounding_box=bbox)


def test_valid_inspection_result_lifecycle():
    """Test complete InspectionResult creation and serialization."""
    bbox = BoundingBox(x=12.0, y=34.0, width=80.0, height=45.0)
    detection = Detection(
        defect_id="def-101",
        defect_type="crack",
        confidence=0.92,
        bounding_box=bbox,
    )
    metadata = ProcessingMetadata(
        execution_time_ms=45.2,
        device="cpu",
        input_resolution=[640, 640, 3]
    )
    result = InspectionResult(
        inspection_id="insp-999",
        component_id="pipe-sec-4b",
        component_type="pipeline",
        image_id="img-00123.jpg",
        model_name="yolov8-industrial",
        model_version="1.0.0",
        detections=[detection],
        processing_metadata=metadata,
    )

    assert result.inspection_id == "insp-999"
    assert len(result.detections) == 1
    assert result.detections[0].defect_type == "crack"
    assert result.processing_metadata.execution_time_ms == 45.2

    # Verify JSON serialization & deserialization
    json_data = result.model_dump_json()
    reconstructed = InspectionResult.model_validate_json(json_data)
    assert reconstructed.inspection_id == result.inspection_id
    assert reconstructed.detections[0].confidence == 0.92


def test_empty_detections_inspection_result():
    """Test valid inspection result with no detected defects (normal/healthy component)."""
    result = InspectionResult(
        inspection_id="insp-normal-01",
        component_id="pipe-sec-1a",
        component_type="pipeline",
        image_id="normal_surface.jpg",
        model_name="yolov8-industrial",
        model_version="1.0.0",
        detections=[],
    )
    assert len(result.detections) == 0


def test_preprocessor_validation():
    """Test ImagePreprocessor input checks."""
    preprocessor = ImagePreprocessor()
    
    # None input
    with pytest.raises(InvalidImageInputError):
        preprocessor.validate(None)

    # Missing file path
    with pytest.raises(InvalidImageInputError):
        preprocessor.validate("non_existent_file.jpg")

    # Unsupported format
    with pytest.raises(InvalidImageInputError):
        preprocessor.validate("some_file.exe")

    # Byte input validation
    assert preprocessor.validate(b"dummy_image_bytes") is True


def test_inference_pipeline_raises_when_unconfigured():
    """Verify InferencePipeline cleanly raises ModelNotConfiguredError without a model."""
    pipeline = InferencePipeline(model=None)
    
    with pytest.raises(ModelNotConfiguredError):
        pipeline.run_inspection(
            image_input=b"valid_byte_stream",
            inspection_id="insp-001",
            component_id="pipe-100",
            component_type="pipeline"
        )


def test_vision_settings_defaults():
    """Test VisionSettings configuration defaults."""
    settings = VisionSettings()
    assert settings.VISION_DEVICE == "cpu"
    assert 0.0 <= settings.VISION_CONFIDENCE_THRESHOLD <= 1.0
    assert settings.VISION_INPUT_SIZE == (640, 640)
