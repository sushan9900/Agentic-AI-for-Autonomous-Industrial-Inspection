"""Core evaluation engine for autonomous industrial inspection vision models (Phase 5A)."""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
import torch
from vision.evaluation.metrics import (
    calculate_polygon_iou,
    compute_confidence_statistics,
    compute_confidence_sweep,
    compute_precision_recall_f1,
    match_image_predictions,
)


def compute_file_sha256(filepath: Union[str, Path]) -> str:
    """Computes SHA-256 checksum of a file for reproducibility tracking."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


class VisionModelEvaluator:
    """
    Reproducible and auditable evaluator for industrial inspection vision models.
    Operates strictly in evaluation-only mode without mutating weights or annotations.
    """

    def __init__(
        self,
        model_path: Union[str, Path] = "experiments/vision/deepcrack/baseline/weights/best.pt",
        data_yaml: Union[str, Path] = "data/processed/deepcrack/yolo/data.yaml",
        images_dir: Union[str, Path] = "data/processed/deepcrack/yolo/images/test",
        labels_dir: Union[str, Path] = "data/processed/deepcrack/yolo/labels/test",
        device: Optional[str] = None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.50
    ) -> None:
        self.model_path = Path(model_path)
        self.data_yaml = Path(data_yaml)
        self.images_dir = Path(images_dir)
        self.labels_dir = Path(labels_dir)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self._model = None

    def _load_model(self) -> None:
        """Loads YOLO model once onto target compute device."""
        if self._model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model checkpoint not found at: {self.model_path}")
            from ultralytics import YOLO
            self._model = YOLO(str(self.model_path))

    def parse_yolo_label(
        self,
        label_file: Path,
        img_w: int,
        img_h: int
    ) -> Tuple[List[List[float]], List[List[List[float]]]]:
        """
        Parses YOLO segmentation label txt file.
        Returns:
            - gt_boxes: list of [xmin, ymin, xmax, ymax] in pixel coordinates
            - gt_polys: list of polygon points [[x1, y1], [x2, y2], ...] in pixel coordinates
        """
        gt_boxes: List[List[float]] = []
        gt_polys: List[List[List[float]]] = []

        if not label_file.exists():
            return gt_boxes, gt_polys

        with open(label_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            if len(parts) < 5:
                continue

            # parts[0] is class_id, rest are x1, y1, x2, y2, ...
            coords = [float(c) for c in parts[1:]]
            if len(coords) % 2 != 0:
                continue

            poly_pts: List[List[float]] = []
            xs: List[float] = []
            ys: List[float] = []

            for i in range(0, len(coords), 2):
                px = float(coords[i] * img_w)
                py = float(coords[i + 1] * img_h)
                poly_pts.append([px, py])
                xs.append(px)
                ys.append(py)

            if xs and ys:
                xmin = max(0.0, float(min(xs)))
                ymin = max(0.0, float(min(ys)))
                xmax = min(float(img_w), float(max(xs)))
                ymax = min(float(img_h), float(max(ys)))
                gt_boxes.append([xmin, ymin, xmax, ymax])
                gt_polys.append(poly_pts)

        return gt_boxes, gt_polys

    def run_ultralytics_validation(self) -> Dict[str, Any]:
        """
        Executes native Ultralytics dataset validation to obtain standardized mAP metrics.
        """
        self._load_model()
        metrics = self._model.val(
            data=str(self.data_yaml),
            split="test",
            device=self.device,
            verbose=False
        )

        return {
            "object_detection": {
                "precision": round(float(metrics.box.mp), 4),
                "recall": round(float(metrics.box.mr), 4),
                "map50": round(float(metrics.box.map50), 4),
                "map50_95": round(float(metrics.box.map), 4)
            },
            "segmentation": {
                "precision": round(float(metrics.seg.mp), 4),
                "recall": round(float(metrics.seg.mr), 4),
                "map50": round(float(metrics.seg.map50), 4),
                "map50_95": round(float(metrics.seg.map), 4)
            }
        }

    def evaluate(self) -> Dict[str, Any]:
        """
        Executes comprehensive full-suite evaluation on the held-out test split.
        Returns complete structured evaluation dictionary.
        """
        start_time = time.perf_counter()
        self._load_model()

        # 1. Capture Environment and Reproducibility Metadata
        import ultralytics
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        
        reproducibility = {
            "checkpoint_path": str(self.model_path).replace("\\", "/"),
            "checkpoint_sha256": compute_file_sha256(self.model_path),
            "model_architecture": "YOLO11n-seg",
            "ultralytics_version": ultralytics.__version__,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
            "gpu_name": gpu_name,
            "dataset_split": "test",
            "dataset_yaml": str(self.data_yaml).replace("\\", "/"),
            "confidence_threshold": self.confidence_threshold,
            "iou_threshold": self.iou_threshold,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 2. Collect Standardized mAP Metrics
        ultralytics_metrics = self.run_ultralytics_validation()

        # 3. Iterate Over Test Images for Per-Image Evaluation & Sweep Cache
        image_files = sorted(list(self.images_dir.glob("*.jpg")) + list(self.images_dir.glob("*.png")))
        reproducibility["test_image_count"] = len(image_files)

        per_image_records: List[Dict[str, Any]] = []
        sweep_data: List[Dict[str, Any]] = []

        total_gt_instances = 0
        total_pred_instances = 0
        total_tp = 0
        total_fp = 0
        total_fn = 0
        all_confidences: List[float] = []
        all_matched_box_ious: List[float] = []
        all_matched_mask_ious: List[float] = []

        images_with_gt = 0
        images_with_preds = 0

        for img_path in image_files:
            stem = img_path.stem
            label_path = self.labels_dir / f"{stem}.txt"

            # Read image metadata
            img_bgr = cv2.imread(str(img_path))
            if img_bgr is None:
                continue
            h, w = img_bgr.shape[:2]

            # Parse Ground Truth
            gt_boxes, gt_polys = self.parse_yolo_label(label_path, w, h)
            n_gt = len(gt_boxes)
            if n_gt > 0:
                images_with_gt += 1
            total_gt_instances += n_gt

            # Inference at baseline threshold 0.05 to capture all candidates for sweep
            t0 = time.perf_counter()
            results = self._model.predict(
                source=str(img_path),
                conf=0.05,
                device=self.device,
                verbose=False
            )
            lat_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            res = results[0] if results else None
            all_raw_boxes: List[List[float]] = []
            all_raw_confs: List[float] = []
            all_raw_polys: List[List[List[float]]] = []

            if res and res.boxes is not None and len(res.boxes) > 0:
                boxes = res.boxes
                masks = res.masks
                for i in range(len(boxes)):
                    xyxy = boxes.xyxy[i].cpu().numpy().tolist()
                    conf = float(boxes.conf[i].cpu().item())
                    all_raw_boxes.append(xyxy)
                    all_raw_confs.append(conf)

                    if masks is not None and len(masks.xy) > i:
                        poly_pts = masks.xy[i].tolist()
                        all_raw_polys.append(poly_pts)
                    else:
                        all_raw_polys.append([])

            # Cache for confidence sweep
            sweep_data.append({
                "filename": img_path.name,
                "gt_boxes": gt_boxes,
                "gt_polys": gt_polys,
                "pred_boxes": all_raw_boxes,
                "pred_confs": all_raw_confs,
                "pred_polys": all_raw_polys
            })

            # Filter at operational threshold (0.25)
            prod_boxes: List[List[float]] = []
            prod_confs: List[float] = []
            prod_polys: List[List[List[float]]] = []

            for i, c in enumerate(all_raw_confs):
                if c >= self.confidence_threshold:
                    prod_boxes.append(all_raw_boxes[i])
                    prod_confs.append(c)
                    prod_polys.append(all_raw_polys[i])
                    all_confidences.append(c)

            n_pred = len(prod_boxes)
            if n_pred > 0:
                images_with_preds += 1
            total_pred_instances += n_pred

            # Deterministic Matching
            match_res = match_image_predictions(
                gt_boxes=gt_boxes,
                pred_boxes=prod_boxes,
                pred_confs=prod_confs,
                gt_polys=gt_polys,
                pred_polys=prod_polys,
                iou_threshold=self.iou_threshold,
                mask_shape=(h, w)
            )

            total_tp += match_res.tp_count
            total_fp += match_res.fp_count
            total_fn += match_res.fn_count
            all_matched_box_ious.extend(match_res.matched_box_ious)
            all_matched_mask_ious.extend(match_res.matched_mask_ious)

            img_prf = compute_precision_recall_f1(match_res.tp_count, match_res.fp_count, match_res.fn_count)

            # Determine evaluation category
            if n_gt == 0 and n_pred == 0:
                eval_status = "NO_DEFECTS_DETECTED"
            elif match_res.tp_count == n_gt and match_res.fp_count == 0:
                eval_status = "PERFECT_MATCH"
            elif match_res.tp_count > 0:
                eval_status = "PARTIAL_DETECTION"
            elif n_gt > 0 and match_res.tp_count == 0:
                eval_status = "FALSE_NEGATIVE_ONLY"
            else:
                eval_status = "FALSE_POSITIVE_ONLY"

            per_image_records.append({
                "filename": img_path.name,
                "image_dimensions": [h, w],
                "ground_truth_count": n_gt,
                "prediction_count": n_pred,
                "true_positive_count": match_res.tp_count,
                "false_positive_count": match_res.fp_count,
                "false_negative_count": match_res.fn_count,
                "precision": img_prf["precision"],
                "recall": img_prf["recall"],
                "f1_score": img_prf["f1_score"],
                "best_prediction_confidence": round(max(prod_confs), 4) if prod_confs else None,
                "inference_latency_ms": lat_ms,
                "box_ious": [round(x, 4) for x in match_res.matched_box_ious],
                "mask_ious": [round(x, 4) for x in match_res.matched_mask_ious],
                "evaluation_status": eval_status
            })

        # 4. Error Analysis
        missed_defects = [r for r in per_image_records if r["ground_truth_count"] > 0 and r["true_positive_count"] == 0]
        high_false_positives = [r for r in per_image_records if r["false_positive_count"] >= 2]
        partial_detections = [r for r in per_image_records if r["true_positive_count"] > 0 and r["false_negative_count"] > 0]
        low_confidence_detections = [
            r for r in per_image_records 
            if r["prediction_count"] > 0 and r["best_prediction_confidence"] is not None and r["best_prediction_confidence"] < 0.35
        ]

        error_analysis = {
            "summary": {
                "total_test_images": len(image_files),
                "images_with_ground_truth": images_with_gt,
                "images_with_predictions": images_with_preds,
                "completely_missed_images_count": len(missed_defects),
                "high_false_positive_images_count": len(high_false_positives),
                "partial_detection_images_count": len(partial_detections),
                "low_confidence_images_count": len(low_confidence_detections)
            },
            "missed_defect_images": [r["filename"] for r in missed_defects],
            "high_false_positive_images": [
                {"filename": r["filename"], "fp_count": r["false_positive_count"], "gt_count": r["ground_truth_count"]}
                for r in high_false_positives
            ],
            "low_confidence_images": [
                {"filename": r["filename"], "best_confidence": r["best_prediction_confidence"]}
                for r in low_confidence_detections
            ]
        }

        # 5. Confidence Statistics & Sweep
        conf_stats = compute_confidence_statistics(all_confidences)
        conf_sweep = compute_confidence_sweep(
            per_image_data=sweep_data,
            thresholds=[0.10, 0.25, 0.40, 0.50, 0.60, 0.70, 0.80],
            iou_threshold=self.iou_threshold
        )

        # 6. Overall Instance Summary
        overall_prf = compute_precision_recall_f1(total_tp, total_fp, total_fn)
        instance_statistics = {
            "total_ground_truth_instances": total_gt_instances,
            "total_predicted_instances": total_pred_instances,
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives": total_fn,
            "instance_precision": overall_prf["precision"],
            "instance_recall": overall_prf["recall"],
            "instance_f1_score": overall_prf["f1_score"],
            "mean_matched_box_iou": round(float(np.mean(all_matched_box_ious)), 4) if all_matched_box_ious else None,
            "mean_matched_mask_iou": round(float(np.mean(all_matched_mask_ious)), 4) if all_matched_mask_ious else None
        }

        total_duration_s = round(time.perf_counter() - start_time, 2)
        reproducibility["total_evaluation_duration_seconds"] = total_duration_s

        return {
            "reproducibility": reproducibility,
            "ultralytics_metrics": ultralytics_metrics,
            "instance_statistics": instance_statistics,
            "confidence_analysis": {
                "distribution": conf_stats,
                "sweep": conf_sweep
            },
            "error_analysis": error_analysis,
            "per_image_records": per_image_records
        }
