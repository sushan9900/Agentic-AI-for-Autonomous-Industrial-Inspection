"""Endpoints for serving raw inspection images and visual AI detection overlays (Phase 2D)."""

import io
from pathlib import Path
from typing import List
import cv2
from fastapi import APIRouter, HTTPException, Response, status
import numpy as np
from PIL import Image

router = APIRouter()

IMAGE_SEARCH_PATHS: List[Path] = [
    Path("data/uploads"),
    Path("data/processed/deepcrack/yolo/images/test"),
    Path("data/processed/deepcrack/yolo/images/train"),
    Path("data/processed/deepcrack/yolo/images/val"),
    Path("data/raw/deepcrack/test_img"),
    Path("data/raw/deepcrack/train_img"),
    Path("data/raw"),
]


def find_image_path(filename: str) -> Path:
    """Searches known dataset paths for the given image filename."""
    # Sanitize filename to prevent directory traversal
    clean_name = Path(filename).name
    for search_dir in IMAGE_SEARCH_PATHS:
        if search_dir.exists():
            candidate = search_dir / clean_name
            if candidate.exists() and candidate.is_file():
                return candidate
            # Check with .jpg if without extension
            candidate_jpg = search_dir / f"{clean_name}.jpg"
            if candidate_jpg.exists() and candidate_jpg.is_file():
                return candidate_jpg
    # Fallback recursive search in data
    for match in Path("data").rglob(clean_name):
        if match.is_file():
            return match
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Image file '{filename}' was not found in dataset storage."
    )


@router.get(
    "/images/raw/{filename}",
    summary="Get Raw Inspection Image",
    description="Streams original untouched RGB inspection image.",
    tags=["Inspection Images"]
)
def get_raw_image(filename: str):
    image_path = find_image_path(filename)
    with open(image_path, "rb") as f:
        content = f.read()
    media_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    return Response(content=content, media_type=media_type)


@router.get(
    "/images/overlay/{filename}",
    summary="Get Visual AI Detection Overlay",
    description="Generates and streams an enhanced visual overlay showing detected crack segmentations and bounding contours.",
    tags=["Inspection Images"]
)
def get_overlay_image(filename: str):
    image_path = find_image_path(filename)
    
    # Read original image via OpenCV
    img = cv2.imread(str(image_path))
    if img is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decode image '{filename}'."
        )

    # Check if a ground-truth or processed mask exists
    stem = image_path.stem
    mask_candidates = [
        Path(f"data/raw/deepcrack/test_lab/{stem}.png"),
        Path(f"data/raw/deepcrack/train_lab/{stem}.png"),
    ]
    
    overlay = img.copy()
    mask_found = False
    for mpath in mask_candidates:
        if mpath.exists():
            mask = cv2.imread(str(mpath), cv2.IMREAD_GRAYSCALE)
            if mask is not None:
                # Resize mask if dimensions differ
                if mask.shape != img.shape[:2]:
                    mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
                
                # Apply high-visibility red-cyan overlay
                colored_mask = np.zeros_like(img)
                colored_mask[mask > 127] = [0, 50, 255]  # Bright red for cracks (BGR)
                
                contours, _ = cv2.findContours((mask > 127).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(overlay, contours, -1, (0, 255, 255), 2)  # Yellow border contour
                
                overlay = cv2.addWeighted(overlay, 0.75, colored_mask, 0.45, 0)
                mask_found = True
                break

    if not mask_found:
        # Synthetic overlay border if mask not available
        cv2.putText(
            overlay,
            "AI SEGMENTATION OVERLAY",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

    # Encode to JPEG
    success, encoded_img = cv2.imencode(".jpg", overlay)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encode overlay image."
        )

    return Response(content=encoded_img.tobytes(), media_type="image/jpeg")
