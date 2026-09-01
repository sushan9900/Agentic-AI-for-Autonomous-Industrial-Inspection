"""Training and evaluation script for YOLO11n-seg on DeepCrack."""

import json
import time
from pathlib import Path
import yaml
from ultralytics import YOLO

CONFIG_PATH = Path("configs/yolo11_deepcrack.yaml")
EXPERIMENT_DIR = Path("experiments/vision/deepcrack/baseline")


def train_and_evaluate():
    print(f"=== Starting YOLO11n-Seg DeepCrack Baseline Training ===")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("Training configuration:")
    for k, v in cfg.items():
        print(f"  {k}: {v}")

    # Initialize YOLO model with official pretrained weights
    model_name = cfg.get("model", "yolo11n-seg.pt")
    print(f"\nInitializing model {model_name}...")
    model = YOLO(model_name)

    start_train_time = time.time()
    # Execute training
    results = model.train(
        data=cfg["data"],
        epochs=cfg.get("epochs", 50),
        imgsz=cfg.get("imgsz", 640),
        batch=cfg.get("batch", 8),
        device=cfg.get("device", 0),
        workers=cfg.get("workers", 2),
        seed=cfg.get("seed", 42),
        patience=cfg.get("patience", 15),
        project=cfg.get("project", "experiments/vision/deepcrack"),
        name=cfg.get("name", "baseline"),
        save=True,
        plots=True,
        exist_ok=True
    )
    train_duration = time.time() - start_train_time
    print(f"\n[OK] Training completed in {train_duration:.1f} seconds ({train_duration/60:.2f} minutes).")

    # Load best checkpoint
    best_weights_path = Path(results.save_dir) / "weights" / "best.pt"
    print(f"\nBest weights saved to: {best_weights_path} (exists: {best_weights_path.exists()})")

    best_model = YOLO(str(best_weights_path))

    # 1. Validation evaluation
    print("\n--- Evaluating on Validation Split ---")
    val_metrics = best_model.val(data=cfg["data"], split="val", imgsz=cfg.get("imgsz", 640), device=cfg.get("device", 0))
    val_box_map50 = float(val_metrics.box.map50)
    val_box_map = float(val_metrics.box.map)
    val_seg_map50 = float(val_metrics.seg.map50)
    val_seg_map = float(val_metrics.seg.map)
    val_precision = float(val_metrics.seg.mp)
    val_recall = float(val_metrics.seg.mr)

    print(f"  Val Seg mAP@50:    {val_seg_map50:.4f}")
    print(f"  Val Seg mAP@50:95: {val_seg_map:.4f}")
    print(f"  Val Seg Precision: {val_precision:.4f}")
    print(f"  Val Seg Recall:    {val_recall:.4f}")

    # 2. Test evaluation (Held-out test set evaluated strictly once)
    print("\n--- Evaluating on Held-Out Test Split ---")
    test_metrics = best_model.val(data=cfg["data"], split="test", imgsz=cfg.get("imgsz", 640), device=cfg.get("device", 0))
    test_box_map50 = float(test_metrics.box.map50)
    test_box_map = float(test_metrics.box.map)
    test_seg_map50 = float(test_metrics.seg.map50)
    test_seg_map = float(test_metrics.seg.map)
    test_precision = float(test_metrics.seg.mp)
    test_recall = float(test_metrics.seg.mr)

    print(f"  Test Seg mAP@50:    {test_seg_map50:.4f}")
    print(f"  Test Seg mAP@50:95: {test_seg_map:.4f}")
    print(f"  Test Seg Precision: {test_precision:.4f}")
    print(f"  Test Seg Recall:    {test_recall:.4f}")

    summary = {
        "model_architecture": "YOLO11n-seg",
        "dataset": "DeepCrack",
        "training_duration_seconds": train_duration,
        "best_weights": str(best_weights_path),
        "validation_metrics": {
            "seg_mAP50": val_seg_map50,
            "seg_mAP50_95": val_seg_map,
            "box_mAP50": val_box_map50,
            "box_mAP50_95": val_box_map,
            "precision": val_precision,
            "recall": val_recall
        },
        "test_metrics": {
            "seg_mAP50": test_seg_map50,
            "seg_mAP50_95": test_seg_map,
            "box_mAP50": test_box_map50,
            "box_mAP50_95": test_box_map,
            "precision": test_precision,
            "recall": test_recall
        }
    }

    metrics_out = Path(results.save_dir) / "eval_metrics.json"
    with open(metrics_out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[OK] Evaluation metrics saved to: {metrics_out}")
    return summary


if __name__ == "__main__":
    train_and_evaluate()
