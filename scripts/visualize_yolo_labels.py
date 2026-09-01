"""Visual QA utility to overlay generated YOLO segmentation polygons onto images."""

from pathlib import Path
import cv2
import numpy as np

YOLO_ROOT = Path("data/processed/deepcrack/yolo")
INSPECTION_DIR = Path("data/processed/inspection/deepcrack_yolo")


def visualize_samples():
    INSPECTION_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = YOLO_ROOT / "images" / "train"
    labels_dir = YOLO_ROOT / "labels" / "train"

    # Select representative samples
    sample_images = sorted(images_dir.glob("*.jpg"))[:10]
    print(f"Generating visual QA overlays for {len(sample_images)} samples in {INSPECTION_DIR}...")

    for img_path in sample_images:
        lbl_path = labels_dir / f"{img_path.stem}.txt"
        if not lbl_path.exists():
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        overlay = img.copy()

        with open(lbl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            if len(parts) < 7:  # class + at least 3 (x, y) pairs
                continue
            coords = [float(x) for x in parts[1:]]
            pts = []
            for i in range(0, len(coords), 2):
                px = int(coords[i] * w)
                py = int(coords[i+1] * h)
                pts.append([px, py])

            pts_arr = np.array(pts, np.int32).reshape((-1, 1, 2))
            # Draw semi-transparent filled polygon in red/cyan
            cv2.fillPoly(overlay, [pts_arr], (0, 0, 255))
            cv2.polylines(img, [pts_arr], isClosed=True, color=(0, 255, 255), thickness=2)

        # Blend overlay
        cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)

        out_path = INSPECTION_DIR / f"overlay_{img_path.name}"
        cv2.imwrite(str(out_path), img)
        print(f"  [OK] Saved QA overlay: {out_path.name}")


if __name__ == "__main__":
    visualize_samples()
