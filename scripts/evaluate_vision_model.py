"""Executable script to run comprehensive vision model evaluation on held-out test data (Phase 5A)."""

import argparse
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vision.evaluation.evaluator import VisionModelEvaluator
from vision.evaluation.report import EvaluationReportGenerator


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate YOLO11n-seg baseline on DeepCrack held-out test split.")
    parser.add_argument(
        "--model",
        type=str,
        default="experiments/vision/deepcrack/baseline/weights/best.pt",
        help="Path to trained YOLO model weights."
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data/processed/deepcrack/yolo/data.yaml",
        help="Path to dataset data.yaml file."
    )
    parser.add_argument(
        "--images",
        type=str,
        default="data/processed/deepcrack/yolo/images/test",
        help="Path to test images directory."
    )
    parser.add_argument(
        "--labels",
        type=str,
        default="data/processed/deepcrack/yolo/labels/test",
        help="Path to test labels directory."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/vision/deepcrack/reports",
        help="Directory to save output evaluation reports."
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Operational confidence threshold (default: 0.25)."
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.50,
        help="IoU matching threshold (default: 0.50)."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 75)
    print("PHASE 5A: COMPUTER VISION MODEL EVALUATION FRAMEWORK")
    print("=" * 75)
    print(f"Model Checkpoint : {args.model}")
    print(f"Dataset YAML     : {args.data}")
    print(f"Test Images Dir  : {args.images}")
    print(f"Confidence Thresh: {args.conf}")
    print(f"IoU Matching Th  : {args.iou}")
    print("-" * 75)

    evaluator = VisionModelEvaluator(
        model_path=args.model,
        data_yaml=args.data,
        images_dir=args.images,
        labels_dir=args.labels,
        confidence_threshold=args.conf,
        iou_threshold=args.iou
    )

    print("Running evaluation on held-out test set...")
    t0 = time.perf_counter()
    eval_result = evaluator.evaluate()
    duration = time.perf_counter() - t0

    # Save reports
    report_gen = EvaluationReportGenerator(output_dir=args.output_dir)
    saved_paths = report_gen.save_all(eval_result)

    rep = eval_result.get("reproducibility", {})
    um = eval_result.get("ultralytics_metrics", {})
    inst = eval_result.get("instance_statistics", {})
    err = eval_result.get("error_analysis", {}).get("summary", {})
    det = um.get("object_detection", {})
    seg = um.get("segmentation", {})

    print("\n" + "=" * 75)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 75)
    print(f"Test Images Evaluated      : {rep.get('test_image_count')}")
    print(f"Total GT Instances         : {inst.get('total_ground_truth_instances')}")
    print(f"Total Predicted Instances  : {inst.get('total_predicted_instances')}")
    print(f"True Positives (TP)        : {inst.get('true_positives')}")
    print(f"False Positives (FP)       : {inst.get('false_positives')}")
    print(f"False Negatives (FN)       : {inst.get('false_negatives')}")
    print("-" * 75)
    print(f"Box Detection Metrics      : Precision={det.get('precision')} | Recall={det.get('recall')} | mAP50={det.get('map50')} | mAP50-95={det.get('map50_95')}")
    print(f"Mask Segmentation Metrics  : Precision={seg.get('precision')} | Recall={seg.get('recall')} | mAP50={seg.get('map50')} | mAP50-95={seg.get('map50_95')}")
    print(f"Instance F1 Score (0.25)   : {inst.get('instance_f1_score')}")
    print("-" * 75)
    print(f"Completely Missed Images   : {err.get('completely_missed_images_count')}")
    print(f"High False Positive Images : {err.get('high_false_positive_images_count')}")
    print(f"Evaluation Execution Time  : {duration:.2f}s")
    print("=" * 75)
    print("\nGenerated Reports:")
    for k, v in saved_paths.items():
        print(f"  {k:20s}: {v}")
    print("=" * 75)


if __name__ == "__main__":
    main()
