"""Deterministic evaluation metrics, IoU matching, and statistical analysis for computer vision inspection."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import cv2
import numpy as np


@dataclass
class MatchPair:
    """Record of a matched ground truth and prediction pair."""
    gt_index: int
    pred_index: int
    iou: float
    confidence: float
    box_iou: Optional[float] = None
    mask_iou: Optional[float] = None


@dataclass
class ImageMatchResult:
    """Per-image instance matching results and confusion counts."""
    true_positives: List[MatchPair] = field(default_factory=list)
    false_positives: List[int] = field(default_factory=list)  # pred indices
    false_negatives: List[int] = field(default_factory=list)  # gt indices
    matched_box_ious: List[float] = field(default_factory=list)
    matched_mask_ious: List[float] = field(default_factory=list)

    @property
    def tp_count(self) -> int:
        return len(self.true_positives)

    @property
    def fp_count(self) -> int:
        return len(self.false_positives)

    @property
    def fn_count(self) -> int:
        return len(self.false_negatives)


def calculate_bbox_iou(
    box1: Union[Sequence[float], np.ndarray],
    box2: Union[Sequence[float], np.ndarray]
) -> float:
    """
    Computes Intersection-over-Union (IoU) between two bounding boxes.
    Format expected: (x_min, y_min, x_max, y_max) in absolute or normalized coordinates.
    """
    x1_min, y1_min, x1_max, y1_max = float(box1[0]), float(box1[1]), float(box1[2]), float(box1[3])
    x2_min, y2_min, x2_max, y2_max = float(box2[0]), float(box2[1]), float(box2[2]), float(box2[3])

    # Calculate intersection coordinates
    inter_xmin = max(x1_min, x2_min)
    inter_ymin = max(y1_min, y2_min)
    inter_xmax = min(x1_max, x2_max)
    inter_ymax = min(y1_max, y2_max)

    inter_w = max(0.0, inter_xmax - inter_xmin)
    inter_h = max(0.0, inter_ymax - inter_ymin)
    intersection = inter_w * inter_h

    area1 = max(0.0, (x1_max - x1_min) * (y1_max - y1_min))
    area2 = max(0.0, (x2_max - x2_min) * (y2_max - y2_min))
    union = area1 + area2 - intersection

    if union <= 0.0:
        return 0.0

    return float(np.clip(intersection / union, 0.0, 1.0))


def polygon_to_mask(
    polygon: Union[Sequence[Tuple[float, float]], Sequence[Sequence[float]], np.ndarray],
    mask_shape: Tuple[int, int]
) -> np.ndarray:
    """
    Rasterizes a polygon into a binary mask of shape (height, width).
    Coordinates can be absolute or normalized.
    """
    h, w = int(mask_shape[0]), int(mask_shape[1])
    mask = np.zeros((h, w), dtype=np.uint8)

    pts = np.array(polygon, dtype=np.float32)
    if len(pts) < 3:
        return mask

    # If coordinates are normalized in [0, 1], scale to pixel coordinates
    if np.all(pts <= 1.05) and (np.max(pts) > 0):
        pts[:, 0] = pts[:, 0] * w
        pts[:, 1] = pts[:, 1] * h

    pts_int = np.int32([pts])
    cv2.fillPoly(mask, pts_int, 1)
    return mask


def calculate_polygon_iou(
    poly1: Union[Sequence[Sequence[float]], np.ndarray],
    poly2: Union[Sequence[Sequence[float]], np.ndarray],
    mask_shape: Tuple[int, int] = (384, 544)
) -> float:
    """
    Computes Intersection-over-Union (IoU) between two 2D polygons by rasterization.
    """
    mask1 = polygon_to_mask(poly1, mask_shape)
    mask2 = polygon_to_mask(poly2, mask_shape)

    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()

    if union == 0:
        return 0.0

    return float(np.clip(intersection / union, 0.0, 1.0))


def match_image_predictions(
    gt_boxes: List[Sequence[float]],
    pred_boxes: List[Sequence[float]],
    pred_confs: List[float],
    gt_polys: Optional[List[Any]] = None,
    pred_polys: Optional[List[Any]] = None,
    iou_threshold: float = 0.50,
    mask_shape: Tuple[int, int] = (384, 544)
) -> ImageMatchResult:
    """
    Performs deterministic greedy matching between ground-truth and prediction instances on an image.
    Matches highest IoU pairs first at or above iou_threshold.
    """
    n_gt = len(gt_boxes)
    n_pred = len(pred_boxes)
    result = ImageMatchResult()

    if n_gt == 0 and n_pred == 0:
        return result

    if n_gt == 0:
        result.false_positives = list(range(n_pred))
        return result

    if n_pred == 0:
        result.false_negatives = list(range(n_gt))
        return result

    # Compute pairwise Box IoU matrix
    iou_matrix = np.zeros((n_gt, n_pred), dtype=np.float32)
    mask_iou_matrix = np.zeros((n_gt, n_pred), dtype=np.float32)

    has_polys = (gt_polys is not None and pred_polys is not None and 
                 len(gt_polys) == n_gt and len(pred_polys) == n_pred)

    for g_idx in range(n_gt):
        for p_idx in range(n_pred):
            b_iou = calculate_bbox_iou(gt_boxes[g_idx], pred_boxes[p_idx])
            iou_matrix[g_idx, p_idx] = b_iou
            if has_polys and gt_polys[g_idx] is not None and pred_polys[p_idx] is not None:
                m_iou = calculate_polygon_iou(gt_polys[g_idx], pred_polys[p_idx], mask_shape)
                mask_iou_matrix[g_idx, p_idx] = m_iou

    # Greedy matching on box IoU
    matched_gt = set()
    matched_pred = set()

    # Flatten and sort candidate pairs by IoU descending
    candidates = []
    for g_idx in range(n_gt):
        for p_idx in range(n_pred):
            candidates.append((iou_matrix[g_idx, p_idx], g_idx, p_idx))

    candidates.sort(key=lambda x: x[0], reverse=True)

    for iou_val, g_idx, p_idx in candidates:
        if iou_val < iou_threshold:
            break
        if g_idx not in matched_gt and p_idx not in matched_pred:
            matched_gt.add(g_idx)
            matched_pred.add(p_idx)
            
            b_iou = float(iou_matrix[g_idx, p_idx])
            m_iou = float(mask_iou_matrix[g_idx, p_idx]) if has_polys else None

            pair = MatchPair(
                gt_index=g_idx,
                pred_index=p_idx,
                iou=b_iou,
                confidence=float(pred_confs[p_idx]),
                box_iou=b_iou,
                mask_iou=m_iou
            )
            result.true_positives.append(pair)
            result.matched_box_ious.append(b_iou)
            if m_iou is not None:
                result.matched_mask_ious.append(m_iou)

    # Remaining unmatched predictions are False Positives
    for p_idx in range(n_pred):
        if p_idx not in matched_pred:
            result.false_positives.append(p_idx)

    # Remaining unmatched ground truths are False Negatives
    for g_idx in range(n_gt):
        if g_idx not in matched_gt:
            result.false_negatives.append(g_idx)

    return result


def compute_precision_recall_f1(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """Computes precision, recall, and F1 score from TP, FP, FN counts."""
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4)
    }


def compute_confidence_statistics(confidences: List[float]) -> Dict[str, Any]:
    """Computes descriptive statistical distribution of prediction confidence values."""
    if not confidences:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
            "p10": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None
        }

    arr = np.array(confidences, dtype=np.float64)
    return {
        "count": int(len(arr)),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "mean": round(float(np.mean(arr)), 4),
        "median": round(float(np.median(arr)), 4),
        "std": round(float(np.std(arr)), 4),
        "p10": round(float(np.percentile(arr, 10)), 4),
        "p25": round(float(np.percentile(arr, 25)), 4),
        "p50": round(float(np.percentile(arr, 50)), 4),
        "p75": round(float(np.percentile(arr, 75)), 4),
        "p90": round(float(np.percentile(arr, 90)), 4),
    }


def compute_confidence_sweep(
    per_image_data: List[Dict[str, Any]],
    thresholds: List[float] = [0.10, 0.25, 0.40, 0.50, 0.60, 0.70, 0.80],
    iou_threshold: float = 0.50,
    mask_shape: Tuple[int, int] = (384, 544)
) -> List[Dict[str, Any]]:
    """
    Evaluates instance detection precision and recall across multiple confidence thresholds.
    """
    sweep_results = []

    for conf_th in thresholds:
        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_preds = 0

        for img_data in per_image_data:
            gt_boxes = img_data.get("gt_boxes", [])
            all_pred_boxes = img_data.get("pred_boxes", [])
            all_pred_confs = img_data.get("pred_confs", [])
            gt_polys = img_data.get("gt_polys", None)
            all_pred_polys = img_data.get("pred_polys", None)

            # Filter by confidence threshold
            filtered_boxes = []
            filtered_confs = []
            filtered_polys = []

            for i, c in enumerate(all_pred_confs):
                if c >= conf_th:
                    filtered_boxes.append(all_pred_boxes[i])
                    filtered_confs.append(c)
                    if all_pred_polys and len(all_pred_polys) > i:
                        filtered_polys.append(all_pred_polys[i])

            total_preds += len(filtered_boxes)

            match_res = match_image_predictions(
                gt_boxes=gt_boxes,
                pred_boxes=filtered_boxes,
                pred_confs=filtered_confs,
                gt_polys=gt_polys,
                pred_polys=filtered_polys if all_pred_polys else None,
                iou_threshold=iou_threshold,
                mask_shape=mask_shape
            )

            total_tp += match_res.tp_count
            total_fp += match_res.fp_count
            total_fn += match_res.fn_count

        prf = compute_precision_recall_f1(total_tp, total_fp, total_fn)
        sweep_results.append({
            "confidence_threshold": conf_th,
            "total_predictions": total_preds,
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives": total_fn,
            "precision": prf["precision"],
            "recall": prf["recall"],
            "f1_score": prf["f1_score"]
        })

    return sweep_results
