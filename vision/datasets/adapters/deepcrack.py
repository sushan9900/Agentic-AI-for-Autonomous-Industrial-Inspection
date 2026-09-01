"""DeepCrack dataset adapter for crack detection and segmentation."""

import re
import struct
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional
from vision.datasets.adapters.base import BaseDatasetAdapter
from vision.datasets.metadata import DatasetMetadata, DatasetSplitInfo, DatasetTaskType, SourceResolution
from vision.datasets.sample import AnnotationType, DatasetSample, ProvenanceRecord


def parse_image_dimensions(file_path: Path) -> tuple[int, int, int]:
    """Extracts (width, height, channels) from JPEG or PNG header without external dependencies."""
    ext = file_path.suffix.lower()
    try:
        with open(file_path, "rb") as f:
            data = f.read(65536)
            if len(data) < 24:
                return 0, 0, 0

            # PNG
            if ext == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
                w, h = struct.unpack(">II", data[16:24])
                color_type = data[25]
                channels = 1 if color_type in (0, 3) else (3 if color_type == 2 else 4)
                return w, h, channels

            # JPEG
            elif ext in {".jpg", ".jpeg"}:
                f.seek(0)
                full_data = f.read()
                i = 2
                while i < len(full_data) - 9:
                    if full_data[i] == 0xFF:
                        marker = full_data[i+1]
                        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                            h, w = struct.unpack(">HH", full_data[i+5:i+9])
                            channels = full_data[i+9]
                            return w, h, channels
                        elif marker in (0xD9, 0xDA):
                            break
                        else:
                            length = struct.unpack(">H", full_data[i+2:i+4])[0]
                            i += 2 + length
                    else:
                        i += 1
    except Exception:
        pass
    return 0, 0, 0


def extract_deepcrack_group_id(stem: str) -> str:
    """
    Extracts group ID from DeepCrack sample stem to prevent spatial/asset leakage.
    Example: '11289-1' -> '11289', '11289-10' -> '11289', 'img_001' -> 'img_001'.
    """
    match = re.match(r"^(.+?)-\d+$", stem)
    if match:
        return match.group(1)
    return stem


class DeepCrackAdapter(BaseDatasetAdapter):
    """Adapter for official DeepCrack crack segmentation dataset."""

    @property
    def dataset_id(self) -> str:
        return "deepcrack"

    def extract_metadata(self) -> DatasetMetadata:
        return DatasetMetadata(
            dataset_name="DeepCrack",
            source="https://github.com/yhlleo/DeepCrack (Liu et al., 2019)",
            version="1.0.0",
            license="Restricted to non-commercial research and educational use",
            annotation_format="Binary PNG ground-truth masks",
            image_count=537,
            categories=["crack"],
            splits=DatasetSplitInfo(train_count=300, test_count=237, total_count=537),
            resolution_info=SourceResolution(min_width=384, max_width=544, min_height=384, max_height=544, typical_resolution="544x384"),
            intended_task=DatasetTaskType.SEMANTIC_SEGMENTATION,
            notes="Paired RGB images and binary crack segmentation masks."
        )

    def discover_samples(self) -> List[DatasetSample]:
        samples: List[DatasetSample] = []
        base_extracted = self.raw_data_dir / "extracted"

        splits_config = [
            ("train", base_extracted / "train_img", base_extracted / "train_lab"),
            ("test", base_extracted / "test_img", base_extracted / "test_lab"),
        ]

        for split_name, img_dir, lab_dir in splits_config:
            if not img_dir.exists() or not lab_dir.exists():
                continue

            img_files = sorted(img_dir.glob("*.jpg"))
            for img_path in img_files:
                stem = img_path.stem
                mask_path = lab_dir / f"{stem}.png"
                
                w, h, channels = parse_image_dimensions(img_path)
                group_id = extract_deepcrack_group_id(stem)

                sample = DatasetSample(
                    dataset_id=self.dataset_id,
                    sample_id=stem,
                    image_path=img_path,
                    annotation_path=mask_path if mask_path.exists() else None,
                    annotation_type=AnnotationType.SEMANTIC_MASK if mask_path.exists() else AnnotationType.UNANNOTATED,
                    source_split=split_name,
                    group_id=group_id,
                    original_labels=["crack"],
                    image_width=w if w > 0 else 544,
                    image_height=h if h > 0 else 384,
                    channels=channels if channels > 0 else 3,
                    metadata={"split": split_name, "raw_stem": stem},
                    provenance=ProvenanceRecord(
                        source_dataset="DeepCrack",
                        source_archive="DeepCrack.zip",
                        source_archive_hash="ec3fc2bee3b71c2cc3c74739cbc51c97b77f78193d08ce3dda0e16d7d41bf585",
                        pipeline_version="1.0.0"
                    )
                )
                samples.append(sample)
        return samples

    def validate_sample(self, sample: DatasetSample) -> List[str]:
        errors: List[str] = []
        if not sample.image_path.exists():
            errors.append(f"Image file does not exist: {sample.image_path}")
        if sample.annotation_path and not sample.annotation_path.exists():
            errors.append(f"Ground truth mask does not exist: {sample.annotation_path}")
        if sample.image_width <= 0 or sample.image_height <= 0:
            errors.append(f"Invalid image dimensions: {sample.image_width}x{sample.image_height}")
        return errors

    def compute_statistics(self, samples: List[DatasetSample]) -> Dict[str, Any]:
        total = len(samples)
        splits = Counter(s.source_split for s in samples)
        groups = set(s.group_id for s in samples)
        res = Counter((s.image_width, s.image_height) for s in samples)

        return {
            "total_samples": total,
            "splits": dict(splits),
            "unique_groups": len(groups),
            "resolutions": [f"{w}x{h} ({cnt})" for (w, h), cnt in res.most_common()],
            "annotation_types": dict(Counter(s.annotation_type.value for s in samples))
        }
