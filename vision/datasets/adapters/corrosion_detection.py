"""Corrosion Detection dataset adapter (Unannotated domain generalization/inference dataset)."""

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List
from vision.datasets.adapters.base import BaseDatasetAdapter
from vision.datasets.adapters.deepcrack import parse_image_dimensions
from vision.datasets.metadata import DatasetMetadata, DatasetSplitInfo, DatasetTaskType, SourceResolution
from vision.datasets.sample import AnnotationType, DatasetSample, ProvenanceRecord


class CorrosionDetectionAdapter(BaseDatasetAdapter):
    """Adapter for Image-based Corrosion Detection dataset (DOI: 10.17632/tbjn6p2gn9.1)."""

    @property
    def dataset_id(self) -> str:
        return "corrosion_detection"

    def extract_metadata(self) -> DatasetMetadata:
        return DatasetMetadata(
            dataset_name="Image-based Corrosion Detection Dataset",
            source="Mendeley Data / 10.17632/tbjn6p2gn9.1 (Jahanshahi et al., 2020)",
            version="1.0.0",
            license="CC BY 4.0",
            annotation_format="Unannotated raw RGB captures",
            image_count=152,
            categories=["corrosion"],
            splits=DatasetSplitInfo(train_count=0, val_count=0, test_count=0, total_count=152),
            resolution_info=SourceResolution(min_width=1704, max_width=8192, min_height=1114, max_height=5461, typical_resolution="3024x3024"),
            intended_task=DatasetTaskType.CLASSIFICATION,
            notes="152 high-resolution raw RGB captures of corroded structural steel and infrastructure."
        )

    def discover_samples(self) -> List[DatasetSample]:
        samples: List[DatasetSample] = []
        img_dir = self.raw_data_dir / "extracted" / "Largeimage"
        if not img_dir.exists():
            return samples

        img_files = sorted(img_dir.glob("*.jpg"))
        for img_path in img_files:
            stem = img_path.stem
            w, h, channels = parse_image_dimensions(img_path)

            sample = DatasetSample(
                dataset_id=self.dataset_id,
                sample_id=stem,
                image_path=img_path,
                annotation_path=None,
                annotation_type=AnnotationType.UNANNOTATED,
                source_split="inference",
                group_id=f"corrosion_asset_{stem}",
                original_labels=["corrosion"],
                image_width=w if w > 0 else 3024,
                image_height=h if h > 0 else 3024,
                channels=channels if channels > 0 else 3,
                metadata={"role": "domain_generalization_inference"},
                provenance=ProvenanceRecord(
                    source_dataset="Image-based Corrosion Detection Dataset",
                    source_archive="Corrosion_Data.zip",
                    source_archive_hash="f667aedcb6be8e25bdd3a454d106f9304953ad4eb5f267f6798b228be397c07a",
                    pipeline_version="1.0.0"
                )
            )
            samples.append(sample)
        return samples

    def validate_sample(self, sample: DatasetSample) -> List[str]:
        errors: List[str] = []
        if not sample.image_path.exists():
            errors.append(f"Image file not found: {sample.image_path}")
        if sample.image_width <= 0 or sample.image_height <= 0:
            errors.append(f"Invalid image dimensions: {sample.image_width}x{sample.image_height}")
        return errors

    def compute_statistics(self, samples: List[DatasetSample]) -> Dict[str, Any]:
        return {
            "total_samples": len(samples),
            "annotation_types": dict(Counter(s.annotation_type.value for s in samples)),
            "width_min": min((s.image_width for s in samples), default=0),
            "width_max": max((s.image_width for s in samples), default=0),
            "height_min": min((s.image_height for s in samples), default=0),
            "height_max": max((s.image_height for s in samples), default=0),
        }
