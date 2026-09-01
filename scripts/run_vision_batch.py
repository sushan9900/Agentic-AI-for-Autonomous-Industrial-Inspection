"""Batch vision inspection runner producing versioned VisionEvidence contracts and summary reports."""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from vision.inference.evidence_builder import EvidenceBuilder
from vision.inference.pipeline import InferencePipeline
from vision.models.yolo_seg import YOLOSegmentationModel
from vision.schemas.evidence import InspectionStatus, VisionEvidence


def parse_args():
    parser = argparse.ArgumentParser(description="Run batch vision inspection inference across a directory of images.")
    parser.add_argument("--input-dir", type=str, required=True, help="Directory containing input images.")
    parser.add_argument("--model", type=str, default="experiments/vision/deepcrack/baseline/weights/best.pt", help="Path to YOLO segmentation weights checkpoint.")
    parser.add_argument("--output-dir", type=str, default="experiments/vision/deepcrack/inference", help="Base directory for batch results.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (0.0 to 1.0).")
    parser.add_argument("--device", type=str, default="0", help="Compute device ('cpu', '0', 'cuda:0').")
    parser.add_argument("--component-prefix", type=str, default="PIPE-SEC", help="Prefix for synthetic component IDs.")
    parser.add_argument("--max-images", type=int, default=None, help="Optional limit on images to process.")
    return parser.parse_args()


def render_overlay(image_path: Path, evidence: VisionEvidence, output_path: Path):
    """Renders visual overlay showing detection ID, bounding box, and confidence."""
    img = cv2.imread(str(image_path))
    if img is None:
        return

    for det in evidence.detections:
        bbox = det.bounding_box
        x1, y1 = int(bbox.x_pixel), int(bbox.y_pixel)
        x2, y2 = int(bbox.x_pixel + bbox.width_pixel), int(bbox.y_pixel + bbox.height_pixel)

        # Draw bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        # Note: Do not render subjective severity (CRITICAL/HIGH) on image; render measurable features
        label = f"{det.detection_id}: {det.defect_type} {det.confidence:.2f}"
        if det.severity_features and det.severity_features.affected_area_percentage:
            label += f" ({det.severity_features.affected_area_percentage:.1f}%)"

        cv2.putText(img, label, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), img)


def run_batch():
    args = parse_args()
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model checkpoint '{model_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    evidence_dir = output_dir / "evidence"
    overlays_dir = output_dir / "overlays"
    artifacts_dir = output_dir / "artifacts"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Starting Batch Vision Inspection ===")
    print(f"  Input Directory: {input_dir}")
    print(f"  Model Weights:   {model_path}")
    print(f"  Confidence:      {args.conf}")
    print(f"  Device:          {args.device}")

    # Discover images
    supported_exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    image_files = sorted([p for p in input_dir.glob("*") if p.suffix.lower() in supported_exts])
    if args.max_images:
        image_files = image_files[:args.max_images]

    print(f"  Discovered {len(image_files)} images to inspect.\n")

    # Load Model
    model = YOLOSegmentationModel(model_path=model_path, device=args.device, confidence_threshold=args.conf)
    model.load()
    pipeline = InferencePipeline(model=model)

    batch_start = time.perf_counter()
    status_counts = {"SUCCESS": 0, "NO_DETECTIONS": 0, "QUALITY_WARNING": 0, "FAILED": 0}
    total_detections = 0
    all_confidences = []
    inference_latencies = []
    failures = []

    for idx, img_p in enumerate(image_files, start=1):
        component_id = f"{args.component_prefix}-{idx:04d}"
        try:
            evidence = pipeline.run_inspection_evidence(
                image_path=str(img_p),
                component_id=component_id,
                confidence_threshold=args.conf
            )

            # Save individual evidence JSON
            ev_file = evidence_dir / f"{img_p.stem}.evidence.json"
            EvidenceBuilder.save_evidence(evidence, ev_file)

            # Render overlay
            overlay_file = overlays_dir / f"overlay_{img_p.name}"
            render_overlay(img_p, evidence, overlay_file)

            # Track statistics
            status_counts[evidence.status.value] += 1
            total_detections += len(evidence.detections)
            for d in evidence.detections:
                all_confidences.append(d.confidence)
            inference_latencies.append(evidence.processing.inference_ms)

            print(f"  [{idx}/{len(image_files)}] {img_p.name} -> {evidence.status.value} (Detections: {len(evidence.detections)}, Inf: {evidence.processing.inference_ms:.1f}ms)")

        except Exception as e:
            status_counts["FAILED"] += 1
            failures.append({"image": img_p.name, "error": str(e)})
            print(f"  [{idx}/{len(image_files)}] {img_p.name} -> FAILED: {e}", file=sys.stderr)

    total_batch_time = (time.perf_counter() - batch_start) * 1000.0
    avg_inf_ms = sum(inference_latencies) / len(inference_latencies) if inference_latencies else 0.0
    avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

    summary = {
        "batch_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_info": model.metadata(),
        "input_directory": str(input_dir),
        "total_images_inspected": len(image_files),
        "successful_inspections": status_counts["SUCCESS"],
        "no_detection_inspections": status_counts["NO_DETECTIONS"],
        "quality_warning_inspections": status_counts["QUALITY_WARNING"],
        "failed_inspections": status_counts["FAILED"],
        "total_defects_detected": total_detections,
        "average_inference_time_ms": round(avg_inf_ms, 2),
        "average_confidence": round(avg_conf, 4),
        "total_batch_duration_ms": round(total_batch_time, 2),
        "failures": failures
    }

    summary_file = output_dir / "batch_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[OK] Batch inspection completed.")
    print(f"  Total Images:        {len(image_files)}")
    print(f"  Success:             {status_counts['SUCCESS']}")
    print(f"  No Detections:       {status_counts['NO_DETECTIONS']}")
    print(f"  Quality Warnings:    {status_counts['QUALITY_WARNING']}")
    print(f"  Total Defects:       {total_detections}")
    print(f"  Avg Inference Time:  {avg_inf_ms:.2f} ms")
    print(f"  Summary saved to:    {summary_file}")
    return summary


if __name__ == "__main__":
    run_batch()
