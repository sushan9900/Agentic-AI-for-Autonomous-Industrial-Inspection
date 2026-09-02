"""Vision model evaluation framework package (Phase 5A)."""

from vision.evaluation.evaluator import VisionModelEvaluator, compute_file_sha256
from vision.evaluation.metrics import (
    ImageMatchResult,
    MatchPair,
    calculate_bbox_iou,
    calculate_polygon_iou,
    compute_confidence_statistics,
    compute_confidence_sweep,
    compute_precision_recall_f1,
    match_image_predictions,
    polygon_to_mask,
)
from vision.evaluation.report import EvaluationReportGenerator

__all__ = [
    "VisionModelEvaluator",
    "EvaluationReportGenerator",
    "compute_file_sha256",
    "calculate_bbox_iou",
    "calculate_polygon_iou",
    "polygon_to_mask",
    "match_image_predictions",
    "compute_precision_recall_f1",
    "compute_confidence_statistics",
    "compute_confidence_sweep",
    "MatchPair",
    "ImageMatchResult",
]
