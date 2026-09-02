"""Unit tests for VisionModelEvaluator helper routines and initialization (Phase 5A)."""

from pathlib import Path
import tempfile
import pytest
from vision.evaluation.evaluator import VisionModelEvaluator, compute_file_sha256


def test_compute_file_sha256():
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write("Hello Autonomous Industrial Inspection")
        temp_path = Path(f.name)

    try:
        sha = compute_file_sha256(temp_path)
        assert isinstance(sha, str)
        assert len(sha) == 64
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_parse_yolo_label():
    evaluator = VisionModelEvaluator(
        model_path="experiments/vision/deepcrack/baseline/weights/best.pt"
    )

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
        # Format: class x1 y1 x2 y2 x3 y3 x4 y4 (normalized)
        f.write("0 0.1 0.1 0.5 0.1 0.5 0.5 0.1 0.5\n")
        temp_label = Path(f.name)

    try:
        gt_boxes, gt_polys = evaluator.parse_yolo_label(temp_label, img_w=100, img_h=100)
        assert len(gt_boxes) == 1
        assert len(gt_polys) == 1
        assert gt_boxes[0] == [10.0, 10.0, 50.0, 50.0]
        assert len(gt_polys[0]) == 4
    finally:
        if temp_label.exists():
            temp_label.unlink()


def test_parse_yolo_label_empty():
    evaluator = VisionModelEvaluator(
        model_path="experiments/vision/deepcrack/baseline/weights/best.pt"
    )
    non_existent = Path("non_existent_label_file_123.txt")
    gt_boxes, gt_polys = evaluator.parse_yolo_label(non_existent, img_w=100, img_h=100)
    assert gt_boxes == []
    assert gt_polys == []


def test_evaluator_init_defaults():
    evaluator = VisionModelEvaluator()
    assert evaluator.confidence_threshold == 0.25
    assert evaluator.iou_threshold == 0.50
    assert evaluator.device in ["cuda", "cpu"]
