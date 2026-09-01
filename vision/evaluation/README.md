# Vision Evaluation Framework

This module specifies the evaluation and benchmark metrics foundation for industrial defect detection models.

## Planned Evaluation Metrics

The validation framework will calculate standard computer vision and operational benchmarks:

| Metric | Target / Description |
|---|---|
| **Precision** | Ratio of true positive detections over total positive predictions |
| **Recall** | Coverage of actual ground truth industrial defects detected |
| **F1-Score** | Harmonic mean of Precision and Recall |
| **IoU (Intersection over Union)** | Spatial overlap accuracy between predicted and ground-truth boxes/masks |
| **mAP@50** | Mean Average Precision at IoU threshold 0.50 |
| **mAP@50:95** | Mean Average Precision across IoU thresholds from 0.50 to 0.95 (COCO standard) |
| **Inference Latency** | End-to-end preprocessing, inference, and postprocessing latency in milliseconds |

## Defect Category Benchmark Tracking

Evaluation will track per-class metrics across initial target industrial defect categories:
- Corrosion
- Crack
- Surface damage
- Coating damage
- Deformation

> [!NOTE]
> Evaluation execution and benchmark runner scripts will be populated once models and evaluation test splits are incorporated in subsequent phases.
