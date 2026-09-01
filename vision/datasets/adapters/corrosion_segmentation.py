"""Corrosion Segmentation dataset adapter for ImageJ .roi patch annotations."""

import struct
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List
from vision.datasets.adapters.base import BaseDatasetAdapter
from vision.datasets.metadata import DatasetMetadata, DatasetSplitInfo, DatasetTaskType, SourceResolution
from vision.datasets.sample import AnnotationType, DatasetSample, ProvenanceRecord


def parse_tiff_dimensions(tiff_path: Path) -> tuple[int, int]:
    """Extracts (width, height) from uncompressed TIFF header."""
    try:
        with open(tiff_path, "rb") as f:
            data = f.read(1024)
            if data[:2] not in (b'II', b'MM'):
                return 0, 0
            endian = '<' if data[:2] == b'II' else '>'
            ifd_off = struct.unpack(f"{endian}I", data[4:8])[0]
            f.seek(ifd_off)
            num_entries = struct.unpack(f"{endian}H", f.read(2))[0]
            w, h = 0, 0
            for _ in range(num_entries):
                entry = f.read(12)
                if len(entry) < 12:
                    break
                tag, tag_type, count, val = struct.unpack(f"{endian}HHI I", entry)
                if tag == 256:
                    w = val
                elif tag == 257:
                    h = val
            return w, h
    except Exception:
        return 0, 0


class CorrosionSegmentationAdapter(BaseDatasetAdapter):
    """Adapter for Images and pixel annotations for corrosion segmentation (DOI: 10.17632/kcyn4nhv2c.1)."""

    @property
    def dataset_id(self) -> str:
        return "corrosion_segmentation"

    def extract_metadata(self) -> DatasetMetadata:
        return DatasetMetadata(
            dataset_name="Images and pixel annotations for corrosion segmentation",
            source="Mendeley Data / 10.17632/kcyn4nhv2c.1 (Rios et al., 2023)",
            version="1.0.0",
            license="CC BY 4.0",
            annotation_format="ImageJ binary .roi coordinate patches",
            image_count=34,
            categories=["Corrosion", "Background"],
            splits=DatasetSplitInfo(train_count=0, val_count=0, test_count=0, total_count=34),
            resolution_info=SourceResolution(min_width=200, max_width=3952, min_height=132, max_height=3380, typical_resolution="1581x956"),
            intended_task=DatasetTaskType.SEMANTIC_SEGMENTATION,
            notes="Field-acquired corrosion images with sparse ImageJ .roi coordinate patch annotations."
        )

    def discover_samples(self) -> List[DatasetSample]:
        samples: List[DatasetSample] = []
        base_dir = self.raw_data_dir / "extracted" / "Labeled images" / "Labeled images"
        orig_dir = base_dir / "Original images"
        corr_dir = base_dir / "Labels" / "Corrosion"
        bg_dir = base_dir / "Labels" / "Background"

        if not orig_dir.exists():
            return samples

        for img_path in sorted(orig_dir.glob("*.tif")):
            stem = img_path.stem
            # e.g. Imag107 -> CorrosionImag107.tif.zip
            corr_zip = corr_dir / f"Corrosion{stem}.tif.zip"
            bg_zip = bg_dir / f"Background{stem}.tif.zip"
            
            w, h = parse_tiff_dimensions(img_path)

            sample = DatasetSample(
                dataset_id=self.dataset_id,
                sample_id=stem,
                image_path=img_path,
                annotation_path=corr_zip if corr_zip.exists() else None,
                annotation_type=AnnotationType.PATCH_ROI,
                source_split="patch_roi",
                group_id=f"puc_rio_{stem}",
                original_labels=["Corrosion", "Background"],
                image_width=w if w > 0 else 1581,
                image_height=h if h > 0 else 956,
                channels=3,
                metadata={
                    "corrosion_rois_zip": str(corr_zip) if corr_zip.exists() else None,
                    "background_rois_zip": str(bg_zip) if bg_zip.exists() else None,
                    "annotation_nature": "sparse_patch_rois"
                },
                provenance=ProvenanceRecord(
                    source_dataset="Images and pixel annotations for corrosion segmentation",
                    source_archive="Labeled images.zip",
                    source_archive_hash="6fbd29524a81f4d8250a3cf978da09ad09d48f65522677792156d0bdf454fcce",
                    pipeline_version="1.0.0"
                )
            )
            samples.append(sample)
        return samples

    def validate_sample(self, sample: DatasetSample) -> List[str]:
        errors: List[str] = []
        if not sample.image_path.exists():
            errors.append(f"Image not found: {sample.image_path}")
        if sample.annotation_type != AnnotationType.PATCH_ROI:
            errors.append(f"Invalid annotation type {sample.annotation_type}; expected PATCH_ROI")
        return errors

    def compute_statistics(self, samples: List[DatasetSample]) -> Dict[str, Any]:
        return {
            "total_samples": len(samples),
            "annotation_type": "patch_roi",
            "classes": ["Corrosion", "Background"]
        }
