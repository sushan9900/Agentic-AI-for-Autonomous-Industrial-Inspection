"""Deterministic computer vision severity feature extraction."""

from typing import List, Optional
from vision.schemas.inspection import BoundingBox, SeverityFeatures


def compute_bounding_box_area_percentage(
    bbox: BoundingBox,
    img_w: int,
    img_h: int
) -> float:
    """Calculates percentage of image area covered by bounding box."""
    if img_w <= 0 or img_h <= 0:
        return 0.0
    box_area = bbox.width * bbox.height
    total_area = float(img_w * img_h)
    return round(min(100.0, (box_area / total_area) * 100.0), 4)


def compute_polygon_area_percentage(
    polygon_points: List[List[float]],
    img_w: int,
    img_h: int
) -> float:
    """
    Computes percentage of image area enclosed by polygon vertices using Shoelace formula.
    Points format: [[x1, y1], [x2, y2], ...]
    """
    if len(polygon_points) < 3 or img_w <= 0 or img_h <= 0:
        return 0.0

    n = len(polygon_points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += polygon_points[i][0] * polygon_points[j][1]
        area -= polygon_points[j][0] * polygon_points[i][1]
    poly_area = abs(area) / 2.0

    # If coordinates are normalized [0, 1]
    is_normalized = all(0.0 <= pt[0] <= 1.0 and 0.0 <= pt[1] <= 1.0 for pt in polygon_points)
    if is_normalized:
        return round(min(100.0, poly_area * 100.0), 4)
    else:
        total_area = float(img_w * img_h)
        return round(min(100.0, (poly_area / total_area) * 100.0), 4)


def estimate_crack_dimensions(
    bbox: BoundingBox,
    polygon_points: Optional[List[List[float]]] = None,
    img_w: int = 640,
    img_h: int = 640
) -> tuple[float, float]:
    """
    Estimates approximate crack length and average width in pixels from bounding box and polygon.
    Returns: (estimated_length_px, estimated_width_px)
    """
    w_px = max(0.0, bbox.width)
    h_px = max(0.0, bbox.height)
    
    # Diagonal of bounding box as conservative upper-bound length
    length_px = round((w_px**2 + h_px**2) ** 0.5, 2)

    if polygon_points and len(polygon_points) >= 3 and length_px > 0:
        # Calculate polygon area in pixels
        area_pct = compute_polygon_area_percentage(polygon_points, img_w, img_h)
        poly_area_px = (area_pct / 100.0) * (img_w * img_h)
        width_px = round(poly_area_px / length_px, 2)
    else:
        width_px = round(min(w_px, h_px), 2)

    return length_px, width_px


def extract_severity_features(
    bbox: BoundingBox,
    img_w: int,
    img_h: int,
    polygon_points: Optional[List[List[float]]] = None,
    location_type: Optional[str] = None
) -> SeverityFeatures:
    """
    Extracts measurable deterministic computer vision properties into a SeverityFeatures schema.
    Does NOT hallucinate subjective severity levels.
    """
    bbox_pct = compute_bounding_box_area_percentage(bbox, img_w, img_h)
    
    affected_pct = 0.0
    if polygon_points:
        affected_pct = compute_polygon_area_percentage(polygon_points, img_w, img_h)
    else:
        affected_pct = bbox_pct

    length_px, width_px = estimate_crack_dimensions(bbox, polygon_points, img_w, img_h)

    return SeverityFeatures(
        affected_area_percentage=affected_pct,
        location_type=location_type,
        estimated_size=f"{length_px}px x {width_px}px",
        spread="localized" if affected_pct < 5.0 else "widespread",
        visual_severity=None  # Leave for agentic reasoning / domain threshold rules
    )
