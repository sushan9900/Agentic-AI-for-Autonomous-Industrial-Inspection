"""Unit tests for vision inference pipeline orchestration and InspectionResult generation."""

import pytest
from pathlib import Path
from vision.inference.pipeline import InferencePipeline
from vision.models.base import BaseVisionModel, ModelNotConfiguredError
from vision.schemas.inspection import BoundingBox, Detection, InspectionResult, SeverityFeatures


class MockVisionModel(BaseVisionModel):
    """Mock vision model for unit testing without GPU/checkpoint dependencies."""

    def __init__(self):
        super().__init__(model_path="mock_model.pt", device="cpu")
        self._is_loaded = True

    def load(self) -> None:
        self._is_loaded = True

    def predict(self, preprocessed_input, confidence_threshold=None):
        bbox = BoundingBox(x=10.0, y=10.0, width=50.0, height=20.0)
        det = Detection(
            defect_id="det_mock_01",
            defect_type="crack",
            confidence=0.88,
            bounding_box=bbox,
            severity_features=SeverityFeatures(
                affected_area_percentage=2.5,
                estimated_size="53.85px x 18.57px",
                spread="localized"
            )
        )
        return [det]

    def metadata(self):
        return {
            "model_type": "MockYOLO",
            "version": "1.0.0",
            "device": "cpu"
        }


def test_inference_pipeline_execution_with_mock_model(tmp_path: Path):
    mock_model = MockVisionModel()
    pipeline = InferencePipeline(model=mock_model)

    # Create dummy image file
    img_file = tmp_path / "test_image.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    result = pipeline.run_inspection(
        image_input=str(img_file),
        inspection_id="insp_test_001",
        component_id="PIPE-VALVE-01",
        component_type="pipeline"
    )

    assert isinstance(result, InspectionResult)
    assert result.inspection_id == "insp_test_001"
    assert result.component_id == "PIPE-VALVE-01"
    assert result.model_name == "MockYOLO"
    assert len(result.detections) == 1
    assert result.detections[0].defect_type == "crack"
    assert result.detections[0].confidence == 0.88
    assert result.processing_metadata.execution_time_ms is not None
    assert result.processing_metadata.execution_time_ms >= 0.0


def test_inference_pipeline_fails_without_loaded_model(tmp_path: Path):
    unloaded_model = MockVisionModel()
    unloaded_model._is_loaded = False

    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    pipeline = InferencePipeline(model=unloaded_model)
    with pytest.raises(ModelNotConfiguredError):
        pipeline.run_inspection(
            image_input=str(img_file),
            inspection_id="insp_002",
            component_id="PIPE-02"
        )
