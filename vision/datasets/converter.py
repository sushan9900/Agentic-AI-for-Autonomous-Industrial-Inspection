from typing import Dict, List, Optional, Tuple, Union
from vision.datasets.coco import COCOAnnotation, COCODataset, COCOImage
from vision.datasets.taxonomy import TaxonomyMapper, UNIFIED_TAXONOMY


class ConversionError(Exception):
    """Base exception for annotation format conversions."""
    pass


class CoordinateNormalizationError(ConversionError):
    """Raised when coordinates cannot be normalized within [0, 1] bounds."""
    pass


class COCOToYOLOConverter:
    """Converts master COCO dataset representation into YOLO format training annotations."""

    def __init__(self, taxonomy_mapper: Optional[TaxonomyMapper] = None) -> None:
        self.taxonomy_mapper = taxonomy_mapper

    @staticmethod
    def normalize_bbox(
        bbox: List[float],
        img_width: int,
        img_height: int
    ) -> Tuple[float, float, float, float]:
        """Converts COCO pixel [x_min, y_min, width, height] to YOLO normalized [x_center, y_center, w, h].
        
        Args:
            bbox: [x_min, y_min, width, height] in pixel coordinates.
            img_width: Source image width in pixels.
            img_height: Source image height in pixels.
            
        Returns:
            Tuple[float, float, float, float]: Normalized (x_center, y_center, width, height) in [0.0, 1.0].
        """
        if img_width <= 0 or img_height <= 0:
            raise CoordinateNormalizationError(
                f"Image dimensions must be positive, got width={img_width}, height={img_height}"
            )

        x_min, y_min, w, h = bbox
        
        # Calculate center coordinates
        x_center = x_min + (w / 2.0)
        y_center = y_min + (h / 2.0)

        # Normalize by image resolution
        norm_x = x_center / float(img_width)
        norm_y = y_center / float(img_height)
        norm_w = w / float(img_width)
        norm_h = h / float(img_height)

        # Clamp and validate boundary constraints
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        norm_w = max(0.0, min(1.0, norm_w))
        norm_h = max(0.0, min(1.0, norm_h))

        return (norm_x, norm_y, norm_w, norm_h)

    @staticmethod
    def normalize_polygon(
        polygon: List[float],
        img_width: int,
        img_height: int
    ) -> List[float]:
        """Normalizes COCO polygon coordinates [x1, y1, x2, y2, ...] into [0.0, 1.0] relative floats.
        
        Args:
            polygon: Flattened polygon vertex coordinates in pixels.
            img_width: Image width in pixels.
            img_height: Image height in pixels.
            
        Returns:
            List[float]: Normalized polygon vertices [norm_x1, norm_y1, ...].
        """
        if len(polygon) < 6 or len(polygon) % 2 != 0:
            raise CoordinateNormalizationError(
                f"Polygon must have at least 3 vertex pairs (6 floats), got {len(polygon)} values."
            )

        normalized = []
        for i in range(0, len(polygon), 2):
            px = polygon[i]
            py = polygon[i + 1]
            nx = max(0.0, min(1.0, px / float(img_width)))
            ny = max(0.0, min(1.0, py / float(img_height)))
            normalized.extend([nx, ny])

        return normalized

    def convert_annotation_to_yolo_box(
        self,
        annotation: COCOAnnotation,
        img_width: int,
        img_height: int,
        category_id_override: Optional[int] = None,
    ) -> str:
        """Formats a single COCO annotation into a YOLO bounding box line: '<class_id> <x_center> <y_center> <w> <h>'."""
        class_id = category_id_override if category_id_override is not None else annotation.category_id
        x_c, y_c, w, h = self.normalize_bbox(annotation.bbox, img_width, img_height)
        return f"{class_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}"

    def convert_annotation_to_yolo_segmentation(
        self,
        annotation: COCOAnnotation,
        img_width: int,
        img_height: int,
        category_id_override: Optional[int] = None,
    ) -> Optional[str]:
        """Formats a single COCO polygon annotation into a YOLO segmentation line: '<class_id> <x1> <y1> <x2> <y2> ...'."""
        class_id = category_id_override if category_id_override is not None else annotation.category_id
        
        if not annotation.segmentation or not isinstance(annotation.segmentation, list):
            # Fallback to bounding box 4-corner polygon if no explicit segmentation polygon exists
            x_min, y_min, w, h = annotation.bbox
            x_max, y_max = x_min + w, y_min + h
            poly = [x_min, y_min, x_max, y_min, x_max, y_max, x_min, y_max]
        else:
            # Use the first polygon in the list
            poly = annotation.segmentation[0]

        norm_poly = self.normalize_polygon(poly, img_width, img_height)
        coords_str = " ".join(f"{c:.6f}" for c in norm_poly)
        return f"{class_id} {coords_str}"
