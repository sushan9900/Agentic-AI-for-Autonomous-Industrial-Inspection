# Vision Model Evaluation Framework (Phase 5A)

## Overview
The `vision.evaluation` module provides a reproducible, auditable, and deterministic evaluation framework for industrial defect segmentation and object detection models.

It operates strictly on the held-out test split without modifying model weights, mutating ground truth annotations, or fabricating metrics.

---

## Core Components

1. **`metrics.py`**:
   - `calculate_bbox_iou(box1, box2)`: Computes bounding box Intersection-over-Union.
   - `calculate_polygon_iou(poly1, poly2, mask_shape)`: Rasterizes polygon contours to compute true mask IoU.
   - `match_image_predictions(...)`: Deterministic greedy bipartite matching between predictions and ground truths at `IoU >= 0.50`.
   - `compute_precision_recall_f1(tp, fp, fn)`: Standard instance-level metrics.
   - `compute_confidence_statistics(confs)`: Descriptive statistical distributions (min, max, mean, median, percentiles).
   - `compute_confidence_sweep(...)`: Precision/Recall sensitivity across thresholds `[0.10, 0.25, 0.40, 0.50, 0.60, 0.70, 0.80]`.

2. **`evaluator.py`**:
   - `VisionModelEvaluator`:
     - Loads model weights and records cryptographic SHA-256 hash.
     - Runs native Ultralytics dataset validation (`mAP50`, `mAP50:95` for Box and Mask).
     - Processes per-image test samples collecting inference latencies, defect matches, and failure classifications.
     - Performs automated error analysis (completely missed defects, high false positives, low-confidence predictions).

3. **`report.py`**:
   - `EvaluationReportGenerator`:
     - Serializes `vision_evaluation.json`.
     - Generates auditable Markdown report `vision_evaluation.md`.
     - Exports per-image records to `per_image_results.json`.
     - Exports failure mode breakdown to `error_analysis.json`.

---

## Usage

Run evaluation CLI:
```bash
.\.venv\Scripts\python.exe scripts/evaluate_vision_model.py
```
