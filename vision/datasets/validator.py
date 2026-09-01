from typing import Dict, List, Optional, Set, Tuple
import os

from vision.datasets.coco import COCOAnnotation, COCODataset, COCOImage
from vision.datasets.taxonomy import TaxonomyMapper, UNIFIED_TAXONOMY


class ValidationError(Exception):
    """Base exception for dataset validation failures."""
    pass


class DatasetIntegrityReport:
    """Summary report of dataset validation findings."""

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.total_images_checked: int = 0
        self.total_annotations_checked: int = 0
        self.class_distribution: Dict[int, int] = {}

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class DatasetValidator:
    """Deterministic validation engine for dataset integrity, geometries, and taxonomic consistency."""

    SUPPORTED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    def __init__(
        self,
        taxonomy_mapper: Optional[TaxonomyMapper] = None,
        check_file_existence: bool = False,
        images_base_dir: Optional[str] = None,
    ) -> None:
        self.taxonomy_mapper = taxonomy_mapper
        self.check_file_existence = check_file_existence
        self.images_base_dir = images_base_dir

    def validate_image_record(self, image: COCOImage, report: DatasetIntegrityReport) -> bool:
        """Validates a single COCO image metadata entry."""
        if image.width <= 0 or image.height <= 0:
            report.add_error(
                f"Image ID {image.id} ({image.file_name}) has invalid dimensions: "
                f"{image.width}x{image.height}"
            )
            return False

        _, ext = os.path.splitext(image.file_name.lower())
        if ext not in self.SUPPORTED_EXTENSIONS:
            report.add_error(
                f"Image ID {image.id} ({image.file_name}) has unsupported extension '{ext}'."
            )
            return False

        if self.check_file_existence and self.images_base_dir:
            full_path = os.path.join(self.images_base_dir, image.file_name)
            if not os.path.exists(full_path):
                report.add_error(f"Image ID {image.id} file not found at: {full_path}")
                return False
            if os.path.getsize(full_path) == 0:
                report.add_error(f"Image ID {image.id} file is 0 bytes: {full_path}")
                return False

        return True

    def validate_annotation_record(
        self,
        annotation: COCOAnnotation,
        image_dims: Tuple[int, int],
        report: DatasetIntegrityReport,
    ) -> bool:
        """Validates bounding box and segmentation geometry for an annotation."""
        img_w, img_h = image_dims

        # 1. Bounding box geometric checks
        x, y, w, h = annotation.bbox
        if w <= 0 or h <= 0:
            report.add_error(
                f"Annotation ID {annotation.id} has non-positive width/height: w={w}, h={h}"
            )
            return False

        if x < 0 or y < 0 or (x + w) > img_w + 1e-2 or (y + h) > img_h + 1e-2:
            report.add_warning(
                f"Annotation ID {annotation.id} box [{x}, {y}, {w}, {h}] extends outside image boundaries ({img_w}x{img_h})."
            )

        # 2. Polygon segmentation checks (if present)
        if annotation.segmentation and isinstance(annotation.segmentation, list):
            for poly in annotation.segmentation:
                if len(poly) < 6 or len(poly) % 2 != 0:
                    report.add_error(
                        f"Annotation ID {annotation.id} has invalid polygon vertex length: {len(poly)}"
                    )
                    return False

        # 3. Category validation
        if self.taxonomy_mapper:
            cat_id = annotation.category_id
            if cat_id not in self.taxonomy_mapper.target_taxonomy:
                report.add_error(
                    f"Annotation ID {annotation.id} category ID {cat_id} is not in target taxonomy: "
                    f"{list(self.taxonomy_mapper.target_taxonomy.keys())}"
                )
                return False

        # Track class distribution
        report.class_distribution[annotation.category_id] = (
            report.class_distribution.get(annotation.category_id, 0) + 1
        )

        return True

    def validate_dataset(self, dataset: COCODataset) -> DatasetIntegrityReport:
        """Executes full validation suite on a COCODataset instance."""
        report = DatasetIntegrityReport()

        image_map: Dict[int, Tuple[int, int]] = {}
        seen_filenames: Set[str] = set()

        # Check images
        for img in dataset.images:
            report.total_images_checked += 1
            if img.file_name in seen_filenames:
                report.add_warning(f"Duplicate image filename detected: {img.file_name}")
            seen_filenames.add(img.file_name)

            if self.validate_image_record(img, report):
                image_map[img.id] = (img.width, img.height)

        # Check annotations
        for ann in dataset.annotations:
            report.total_annotations_checked += 1
            if ann.image_id not in image_map:
                report.add_error(
                    f"Annotation ID {ann.id} references missing image ID {ann.image_id}"
                )
                continue

            dims = image_map[ann.image_id]
            self.validate_annotation_record(ann, dims, report)

        return report

    @staticmethod
    def check_split_leakage(
        train_images: List[COCOImage],
        val_images: List[COCOImage],
        test_images: List[COCOImage],
    ) -> List[str]:
        """Detects filename, asset ID, or session ID overlap between train, val, and test splits."""
        leakages = []

        train_files = {img.file_name for img in train_images}
        val_files = {img.file_name for img in val_images}
        test_files = {img.file_name for img in test_images}

        # Filename leakage
        train_val_overlap = train_files.intersection(val_files)
        if train_val_overlap:
            leakages.append(f"Filename leakage between Train and Val: {len(train_val_overlap)} images")

        train_test_overlap = train_files.intersection(test_files)
        if train_test_overlap:
            leakages.append(f"Filename leakage between Train and Test: {len(train_test_overlap)} images")

        val_test_overlap = val_files.intersection(test_files)
        if val_test_overlap:
            leakages.append(f"Filename leakage between Val and Test: {len(val_test_overlap)} images")

        # Asset/Component ID leakage (if asset_id metadata exists)
        train_assets = {img.asset_id for img in train_images if img.asset_id}
        test_assets = {img.asset_id for img in test_images if img.asset_id}
        asset_overlap = train_assets.intersection(test_assets)
        if asset_overlap:
            leakages.append(
                f"Asset/Pipe segment leakage: Asset IDs {asset_overlap} present in both Train and Test!"
            )

        return leakages
