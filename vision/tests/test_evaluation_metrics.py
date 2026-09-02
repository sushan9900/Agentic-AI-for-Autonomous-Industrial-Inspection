"""Unit tests for vision evaluation metrics, IoU matching, and statistical distributions (Phase 5A)."""

import pytest
import numpy as np
from vision.evaluation.metrics import (
    calculate_bbox_iou,
    calculate_polygon_iou,
    compute_confidence_statistics,
    compute_confidence_sweep,
    compute_precision_recall_f1,
    match_image_predictions,
    polygon_to_mask,
)


def test_calculate_bbox_iou_perfect_match():
    boxA = [10.0, 10.0, 50.0, 50.0]
    boxB = [10.0, 10.0, 50.0, 50.0]
    iou = calculate_bbox_iou(boxA, boxB)
    assert iou == pytest.approx(1.0, rel=1e-4)


def test_calculate_bbox_iou_disjoint():
    boxA = [0.0, 0.0, 10.0, 10.0]
    boxB = [20.0, 20.0, 30.0, 30.0]
    iou = calculate_bbox_iou(boxA, boxB)
    assert iou == 0.0


def test_calculate_bbox_iou_partial():
    # Box A: [0, 0, 10, 10] -> area 100
    # Box B: [5, 0, 15, 10] -> area 100
    # Intersection: [5, 0, 10, 10] -> area 50
    # Union: 100 + 100 - 50 = 150
    # IoU = 50 / 150 = 1/3
    boxA = [0.0, 0.0, 10.0, 10.0]
    boxB = [5.0, 0.0, 15.0, 10.0]
    iou = calculate_bbox_iou(boxA, boxB)
    assert iou == pytest.approx(1.0 / 3.0, rel=1e-4)


def test_calculate_polygon_iou_identical():
    polyA = [[10.0, 10.0], [50.0, 10.0], [50.0, 50.0], [10.0, 50.0]]
    polyB = [[10.0, 10.0], [50.0, 10.0], [50.0, 50.0], [10.0, 50.0]]
    iou = calculate_polygon_iou(polyA, polyB, mask_shape=(100, 100))
    assert iou == pytest.approx(1.0, rel=1e-4)


def test_calculate_polygon_iou_disjoint():
    polyA = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
    polyB = [[20.0, 20.0], [30.0, 20.0], [30.0, 30.0], [20.0, 30.0]]
    iou = calculate_polygon_iou(polyA, polyB, mask_shape=(100, 100))
    assert iou == 0.0


def test_match_image_predictions_perfect():
    gt_boxes = [[10.0, 10.0, 50.0, 50.0]]
    pred_boxes = [[10.0, 10.0, 50.0, 50.0]]
    pred_confs = [0.85]

    result = match_image_predictions(
        gt_boxes=gt_boxes,
        pred_boxes=pred_boxes,
        pred_confs=pred_confs,
        iou_threshold=0.50
    )

    assert result.tp_count == 1
    assert result.fp_count == 0
    assert result.fn_count == 0
    assert len(result.true_positives) == 1
    assert result.true_positives[0].iou == pytest.approx(1.0, rel=1e-4)


def test_match_image_predictions_false_positive():
    gt_boxes = []
    pred_boxes = [[10.0, 10.0, 50.0, 50.0]]
    pred_confs = [0.75]

    result = match_image_predictions(
        gt_boxes=gt_boxes,
        pred_boxes=pred_boxes,
        pred_confs=pred_confs
    )

    assert result.tp_count == 0
    assert result.fp_count == 1
    assert result.fn_count == 0


def test_match_image_predictions_false_negative():
    gt_boxes = [[10.0, 10.0, 50.0, 50.0]]
    pred_boxes = []
    pred_confs = []

    result = match_image_predictions(
        gt_boxes=gt_boxes,
        pred_boxes=pred_boxes,
        pred_confs=pred_confs
    )

    assert result.tp_count == 0
    assert result.fp_count == 0
    assert result.fn_count == 1


def test_match_image_predictions_below_threshold():
    # Overlap only 0.25 < 0.50
    gt_boxes = [[0.0, 0.0, 10.0, 10.0]]
    pred_boxes = [[6.0, 0.0, 16.0, 10.0]]
    pred_confs = [0.90]

    result = match_image_predictions(
        gt_boxes=gt_boxes,
        pred_boxes=pred_boxes,
        pred_confs=pred_confs,
        iou_threshold=0.50
    )

    assert result.tp_count == 0
    assert result.fp_count == 1
    assert result.fn_count == 1


def test_compute_precision_recall_f1():
    # 4 TP, 1 FP, 1 FN
    # Precision = 4 / (4 + 1) = 0.8
    # Recall = 4 / (4 + 1) = 0.8
    # F1 = 0.8
    res = compute_precision_recall_f1(tp=4, fp=1, fn=1)
    assert res["precision"] == 0.8
    assert res["recall"] == 0.8
    assert res["f1_score"] == 0.8

    # Zero division check
    res_zero = compute_precision_recall_f1(tp=0, fp=0, fn=0)
    assert res_zero["precision"] == 0.0
    assert res_zero["recall"] == 0.0
    assert res_zero["f1_score"] == 0.0


def test_compute_confidence_statistics():
    confs = [0.25, 0.50, 0.75, 0.80, 0.90]
    stats = compute_confidence_statistics(confs)
    assert stats["count"] == 5
    assert stats["min"] == 0.25
    assert stats["max"] == 0.90
    assert stats["median"] == 0.75
    assert stats["mean"] == pytest.approx(0.64, rel=1e-2)

    # Empty list check
    empty_stats = compute_confidence_statistics([])
    assert empty_stats["count"] == 0
    assert empty_stats["min"] is None


def test_compute_confidence_sweep():
    img_data = [{
        "gt_boxes": [[10.0, 10.0, 50.0, 50.0]],
        "pred_boxes": [[10.0, 10.0, 50.0, 50.0], [60.0, 60.0, 90.0, 90.0]],
        "pred_confs": [0.85, 0.30]
    }]

    sweep = compute_confidence_sweep(
        per_image_data=img_data,
        thresholds=[0.25, 0.50, 0.90]
    )

    assert len(sweep) == 3
    # At 0.25: 2 predictions (1 TP, 1 FP) -> Precision = 0.5, Recall = 1.0
    assert sweep[0]["confidence_threshold"] == 0.25
    assert sweep[0]["total_predictions"] == 2
    assert sweep[0]["true_positives"] == 1
    assert sweep[0]["false_positives"] == 1

    # At 0.50: 1 prediction (1 TP, 0 FP) -> Precision = 1.0, Recall = 1.0
    assert sweep[1]["confidence_threshold"] == 0.50
    assert sweep[1]["total_predictions"] == 1
    assert sweep[1]["true_positives"] == 1
    assert sweep[1]["false_positives"] == 0

    # At 0.90: 0 predictions -> Precision = 0.0, Recall = 0.0, FN = 1
    assert sweep[2]["confidence_threshold"] == 0.90
    assert sweep[2]["total_predictions"] == 0
    assert sweep[2]["false_negatives"] == 1
