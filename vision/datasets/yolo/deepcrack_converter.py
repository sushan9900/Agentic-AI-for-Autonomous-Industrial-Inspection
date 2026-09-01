"""DeepCrack binary mask to YOLO segmentation label converter."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple
import cv2
import numpy as np


class DeepCrackYOLOConverter:
    """Converts DeepCrack paired dataset into Ultralytics YOLO segmentation dataset structure."""

    def __init__(
        self,
        processed_manifest_path: Path = Path("data/processed/deepcrack/manifest.json"),
        yolo_output_dir: Path = Path("data/processed/deepcrack/yolo"),
        min_contour_area: float = 10.0,
        polygon_epsilon_ratio: float = 0.001,
    ):
        self.processed_manifest_path = Path(processed_manifest_path)
        self.yolo_output_dir = Path(yolo_output_dir)
        self.min_contour_area = min_contour_area
        self.polygon_epsilon_ratio = polygon_epsilon_ratio

    def mask_to_yolo_polygons(
        self,
        mask_path: Path,
        img_width: int,
        img_height: int
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """
        Extracts normalized YOLO polygon contours from a binary mask.
        Format per polygon: [x1, y1, x2, y2, ..., xn, yn] normalized to [0.0, 1.0].
        """
        stats = {
            "total_contours_found": 0,
            "contours_retained": 0,
            "contours_discarded_small_area": 0,
            "contours_discarded_insufficient_points": 0,
        }

        if not mask_path.exists():
            return [], stats

        # Read binary mask as grayscale
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            return [], stats

        h, w = mask.shape
        if w != img_width or h != img_height:
            # Reconcile dimensions with mask
            img_width, img_height = w, h

        # Threshold mask to strictly binary (0 or 255)
        _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

        # Find external contours with simple approximation
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
        stats["total_contours_found"] = len(contours)

        polygons: List[List[float]] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_contour_area:
                stats["contours_discarded_small_area"] += 1
                continue

            # Simplify polygon slightly to reduce redundant collinear vertices
            peri = cv2.arcLength(cnt, closed=True)
            epsilon = max(0.5, peri * self.polygon_epsilon_ratio)
            approx = cv2.approxPolyDP(cnt, epsilon=epsilon, closed=True)

            if len(approx) < 3:
                stats["contours_discarded_insufficient_points"] += 1
                continue

            # Flatten and normalize coordinates to [0.0, 1.0]
            normalized_pts: List[float] = []
            for pt in approx:
                px, py = pt[0]
                norm_x = min(max(px / img_width, 0.0), 1.0)
                norm_y = min(max(py / img_height, 0.0), 1.0)
                normalized_pts.extend([round(norm_x, 6), round(norm_y, 6)])

            if len(normalized_pts) >= 6:  # At least 3 (x, y) pairs
                polygons.append(normalized_pts)
                stats["contours_retained"] += 1

        return polygons, stats

    def convert_dataset(self) -> Dict[str, Any]:
        """Executes full conversion of DeepCrack splits to YOLO segmentation format."""
        if not self.processed_manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.processed_manifest_path}")

        with open(self.processed_manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        splits_data = manifest.get("splits", {})
        report: Dict[str, Any] = {
            "total_images_processed": 0,
            "split_counts": {},
            "total_polygons_generated": 0,
            "images_with_annotations": 0,
            "images_without_annotations": 0,
            "contour_stats": {
                "total_contours_found": 0,
                "retained": 0,
                "discarded_small_area": 0,
                "discarded_insufficient_points": 0,
            },
            "failures": []
        }

        # Create output directories
        for split_name in ["train", "val", "test"]:
            (self.yolo_output_dir / "images" / split_name).mkdir(parents=True, exist_ok=True)
            (self.yolo_output_dir / "labels" / split_name).mkdir(parents=True, exist_ok=True)

        for split_name, samples in splits_data.items():
            report["split_counts"][split_name] = len(samples)
            print(f"Converting DeepCrack split '{split_name}' ({len(samples)} samples)...")

            for sample_dict in samples:
                sample_id = sample_dict["sample_id"]
                img_path = Path(sample_dict["image_path"])
                mask_path = Path(sample_dict["annotation_path"]) if sample_dict.get("annotation_path") else None
                w = sample_dict["image_width"]
                h = sample_dict["image_height"]

                # Destination paths
                dest_img_path = self.yolo_output_dir / "images" / split_name / f"{sample_id}.jpg"
                dest_lbl_path = self.yolo_output_dir / "labels" / split_name / f"{sample_id}.txt"

                # Copy image file
                if not dest_img_path.exists():
                    shutil.copy2(img_path, dest_img_path)

                polygons: List[List[float]] = []
                if mask_path and mask_path.exists():
                    polygons, c_stats = self.mask_to_yolo_polygons(mask_path, w, h)
                    report["contour_stats"]["total_contours_found"] += c_stats["total_contours_found"]
                    report["contour_stats"]["retained"] += c_stats["contours_retained"]
                    report["contour_stats"]["discarded_small_area"] += c_stats["contours_discarded_small_area"]
                    report["contour_stats"]["discarded_insufficient_points"] += c_stats["contours_discarded_insufficient_points"]

                # Write YOLO segmentation label file (class_id = 0 for crack)
                with open(dest_lbl_path, "w", encoding="utf-8") as lf:
                    for poly in polygons:
                        poly_str = " ".join(f"{coord:.6f}" for coord in poly)
                        lf.write(f"0 {poly_str}\n")

                report["total_images_processed"] += 1
                if polygons:
                    report["images_with_annotations"] += 1
                    report["total_polygons_generated"] += len(polygons)
                else:
                    report["images_without_annotations"] += 1

        # Generate data.yaml (relative paths for portability)
        data_yaml_path = self.yolo_output_dir / "data.yaml"
        yaml_content = f"""# Ultralytics YOLO11 Segmentation Dataset Configuration for DeepCrack
path: {self.yolo_output_dir.resolve().as_posix()}
train: images/train
val: images/val
test: images/test

names:
  0: crack
"""
        with open(data_yaml_path, "w", encoding="utf-8") as yf:
            yf.write(yaml_content)

        # Save conversion report
        report_path = self.yolo_output_dir / "conversion_report.json"
        with open(report_path, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2)

        print(f"\n[OK] YOLO dataset conversion complete.")
        print(f"  Total images: {report['total_images_processed']}")
        print(f"  Total polygons: {report['total_polygons_generated']}")
        print(f"  YAML config: {data_yaml_path}")
        print(f"  Report: {report_path}")
        return report


if __name__ == "__main__":
    converter = DeepCrackYOLOConverter()
    converter.convert_dataset()
