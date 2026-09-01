"""Unit tests for YOLO segmentation model wrapper, polygon extraction, and severity features."""

import pytest
from pathlib import Path
from vision.datasets.yolo.deepcrack_converter import DeepCrackYOLOConverter
from vision.inference.severity import (
    compute_bounding_box_area_percentage,
    compute_polygon_area_percentage,
    estimate_crack_dimensions,
    extract_severity_features,
)
from vision.models.base import ModelNotConfiguredError
from vision.models.yolo_seg import YOLOSegmentationModel
from vision.schemas.inspection import BoundingBox, Detection


def test_polygon_area_shoelace_calculation():
    # 10x10 square in a 100x100 image
    # Corners: (10, 10), (20, 10), (20, 20), (10, 20) -> Area = 100 -> 1.0%
    pts = [[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0]]
    pct = compute_polygon_area_percentage(pts, img_w=100, img_h=100)
    assert pct == pytest.approx(1.0, rel=1e-2)


def test_bounding_box_area_percentage():
    bbox = BoundingBox(x=10.0, y=10.0, width=20.0, height=50.0)
    pct = compute_bounding_box_area_percentage(bbox, img_w=100, img_h=100)
    assert pct == pytest.approx(10.0, rel=1e-2)


def test_estimate_crack_dimensions():
    bbox = BoundingBox(x=0.0, y=0.0, width=30.0, height=40.0)
    length, width = estimate_crack_dimensions(bbox, img_w=100, img_h=100)
    # Diagonal of 30, 40 = 50.0
    assert length == 50.0
    assert width == 30.0


def test_extract_severity_features_deterministic():
    bbox = BoundingBox(x=10.0, y=10.0, width=20.0, height=20.0)
    features = extract_severity_features(bbox, img_w=100, img_h=100)
    assert features.affected_area_percentage == 4.0
    assert features.estimated_size is not None
    assert features.visual_severity is None  # Must remain None for agentic layer


def test_yolo_segmentation_model_raises_when_not_loaded():
    model = YOLOSegmentationModel(model_path="non_existent.pt")
    assert not model.is_loaded
    with pytest.raises(ModelNotConfiguredError):
        model.predict("test.jpg")


def test_yolo_segmentation_model_load_fails_on_missing_file():
    model = YOLOSegmentationModel(model_path="invalid_path/model.pt")
    with pytest.raises(ModelNotConfiguredError):
        model.load()


def test_yolo_segmentation_model_metadata():
    model = YOLOSegmentationModel(model_path="dummy.pt", device="cpu", confidence_threshold=0.35)
    meta = model.metadata()
    assert meta["model_type"] == "YOLO11n-seg"
    assert meta["confidence_threshold"] == 0.35
    assert meta["is_loaded"] is False
