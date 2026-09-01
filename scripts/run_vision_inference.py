import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
from vision.inference.pipeline import InferencePipeline
from vision.models.yolo_seg import YOLOSegmentationModel


def parse_args():
    parser = argparse.ArgumentParser(description="Run vision inspection inference on an industrial image.")
    parser.add_argument("--image", type=str, required=True, help="Path to input image file.")
    parser.add_argument("--model", type=str, default="experiments/vision/deepcrack/baseline/weights/best.pt", help="Path to YOLO segmentation weights checkpoint.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence detection threshold (0.0 to 1.0).")
    parser.add_argument("--device", type=str, default="0", help="Inference device ('cpu', '0', 'cuda:0').")
    parser.add_argument("--component-id", type=str, default="PIPE-SEG-4021", help="Component ID being inspected.")
    parser.add_argument("--save-overlay", action="store_true", help="Save visualization overlay image.")
    parser.add_argument("--output-dir", type=str, default="experiments/vision/deepcrack/inference", help="Directory for overlay output.")
    return parser.parse_args()


def render_overlay(image_path: Path, inspection_result, output_path: Path):
    img = cv2.imread(str(image_path))
    if img is None:
        return
    h, w = img.shape[:2]
    overlay = img.copy()

    for det in inspection_result.detections:
        bbox = det.bounding_box
        x1, y1 = int(bbox.x), int(bbox.y)
        x2, y2 = int(bbox.x + bbox.width), int(bbox.y + bbox.height)

        # Draw bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"{det.defect_type} {det.confidence:.2f}"
        if det.severity_features and det.severity_features.affected_area_percentage:
            label += f" ({det.severity_features.affected_area_percentage:.1f}%)"

        cv2.putText(img, label, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), img)
    print(f"[OK] Visual overlay saved to: {output_path}")


def main():
    args = parse_args()
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Input image '{image_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model weights checkpoint '{model_path}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading YOLO11-Seg model from: {model_path} (device: {args.device})...")
    model = YOLOSegmentationModel(model_path=model_path, device=args.device, confidence_threshold=args.conf)
    model.load()

    pipeline = InferencePipeline(model=model)

    print(f"Running inspection on: {image_path} (Component: {args.component_id})...")
    result = pipeline.run_inspection(
        image_input=str(image_path),
        inspection_id="insp_cli_001",
        component_id=args.component_id,
        confidence_threshold=args.conf
    )

    print("\n================== INSPECTION RESULT =================")
    print(result.model_dump_json(indent=2))
    print("======================================================")

    if args.save_overlay:
        out_dir = Path(args.output_dir)
        out_file = out_dir / f"overlay_{image_path.name}"
        render_overlay(image_path, result, out_file)


if __name__ == "__main__":
    main()
