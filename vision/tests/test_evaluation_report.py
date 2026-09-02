"""Unit tests for evaluation report generation and serialization (Phase 5A)."""

import json
from pathlib import Path
import tempfile
import pytest
from vision.evaluation.report import EvaluationReportGenerator


@pytest.fixture
def sample_evaluation_data():
    return {
        "reproducibility": {
            "checkpoint_path": "experiments/vision/deepcrack/baseline/weights/best.pt",
            "checkpoint_sha256": "abc123456789",
            "model_architecture": "YOLO11n-seg",
            "ultralytics_version": "8.4.136",
            "torch_version": "2.6.0",
            "cuda_available": True,
            "cuda_version": "12.4",
            "gpu_name": "NVIDIA GeForce RTX 3050",
            "dataset_split": "test",
            "dataset_yaml": "data/processed/deepcrack/yolo/data.yaml",
            "confidence_threshold": 0.25,
            "iou_threshold": 0.50,
            "test_image_count": 86,
            "timestamp": "2026-09-01T12:00:00Z",
            "total_evaluation_duration_seconds": 12.5
        },
        "ultralytics_metrics": {
            "object_detection": {
                "precision": 0.5210,
                "recall": 0.4650,
                "map50": 0.3990,
                "map50_95": 0.2110
            },
            "segmentation": {
                "precision": 0.5150,
                "recall": 0.4030,
                "map50": 0.3440,
                "map50_95": 0.1100
            }
        },
        "instance_statistics": {
            "total_ground_truth_instances": 340,
            "total_predicted_instances": 210,
            "true_positives": 150,
            "false_positives": 60,
            "false_negatives": 190,
            "instance_precision": 0.7143,
            "instance_recall": 0.4412,
            "instance_f1_score": 0.5455,
            "mean_matched_box_iou": 0.6850,
            "mean_matched_mask_iou": 0.5920
        },
        "confidence_analysis": {
            "distribution": {
                "count": 210,
                "min": 0.2510,
                "max": 0.9420,
                "mean": 0.6120,
                "median": 0.6350,
                "std": 0.1820,
                "p10": 0.3120,
                "p25": 0.4500,
                "p50": 0.6350,
                "p75": 0.7800,
                "p90": 0.8650
            },
            "sweep": [
                {
                    "confidence_threshold": 0.25,
                    "total_predictions": 210,
                    "true_positives": 150,
                    "false_positives": 60,
                    "false_negatives": 190,
                    "precision": 0.7143,
                    "recall": 0.4412,
                    "f1_score": 0.5455
                }
            ]
        },
        "error_analysis": {
            "summary": {
                "total_test_images": 86,
                "images_with_ground_truth": 86,
                "images_with_predictions": 80,
                "completely_missed_images_count": 6,
                "high_false_positive_images_count": 3,
                "partial_detection_images_count": 30,
                "low_confidence_images_count": 12
            },
            "missed_defect_images": ["11119.jpg"],
            "high_false_positive_images": [{"filename": "11134.jpg", "fp_count": 3, "gt_count": 2}],
            "low_confidence_images": [{"filename": "11175.jpg", "best_confidence": 0.28}]
        },
        "per_image_records": [
            {
                "filename": "11112.jpg",
                "image_dimensions": [384, 544],
                "ground_truth_count": 3,
                "prediction_count": 3,
                "true_positive_count": 3,
                "false_positive_count": 0,
                "false_negative_count": 0,
                "precision": 1.0,
                "recall": 1.0,
                "f1_score": 1.0,
                "best_prediction_confidence": 0.89,
                "inference_latency_ms": 11.2,
                "box_ious": [0.82, 0.79, 0.75],
                "mask_ious": [0.74, 0.71, 0.68],
                "evaluation_status": "PERFECT_MATCH"
            }
        ]
    }


def test_evaluation_report_generator_save_all(sample_evaluation_data):
    with tempfile.TemporaryDirectory() as temp_dir:
        generator = EvaluationReportGenerator(output_dir=temp_dir)
        paths = generator.save_all(sample_evaluation_data)

        assert paths["json_report"].exists()
        assert paths["markdown_report"].exists()
        assert paths["per_image_report"].exists()
        assert paths["error_report"].exists()

        # Check JSON loadable
        with open(paths["json_report"], "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["reproducibility"]["test_image_count"] == 86

        with open(paths["per_image_report"], "r", encoding="utf-8") as f:
            per_img = json.load(f)
            assert len(per_img) == 1
            assert per_img[0]["filename"] == "11112.jpg"


def test_markdown_generation_content(sample_evaluation_data):
    generator = EvaluationReportGenerator()
    md = generator.generate_markdown(sample_evaluation_data)

    assert "# Autonomous Industrial Inspection — Vision Model Evaluation Audit Report" in md
    assert "[FACT]" in md
    assert "[MEASURED]" in md
    assert "YOLO11n-seg" in md
    assert "0.3990" in md  # box mAP50
    assert "0.3440" in md  # mask mAP50
    assert "11119.jpg" in md  # missed defect sample
