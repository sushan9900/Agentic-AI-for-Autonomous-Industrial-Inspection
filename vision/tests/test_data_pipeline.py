"""Unit tests for production computer vision data pipeline, adapters, splitting, and preprocessing."""

import pytest
from pathlib import Path
from vision.datasets.adapters.corrosion_detection import CorrosionDetectionAdapter
from vision.datasets.adapters.corrosion_segmentation import CorrosionSegmentationAdapter
from vision.datasets.adapters.deepcrack import DeepCrackAdapter, extract_deepcrack_group_id
from vision.datasets.augmentation import AugmentationConfig, AugmentationPipeline
from vision.datasets.leakage import GroupLeakageError, validate_group_leakage
from vision.datasets.preprocessing import (
    ImageResizeMode,
    compute_letterbox_geometry,
    letterbox_mask_2d,
    nearest_neighbor_resize_2d,
    validate_binary_mask_discrete_values,
)
from vision.datasets.sample import AnnotationType, DatasetSample, ProvenanceRecord
from vision.datasets.splitter import DatasetSplitter


def test_dataset_sample_contract_validation(tmp_path: Path):
    img_p = tmp_path / "test.jpg"
    img_p.write_bytes(b"dummy")

    sample = DatasetSample(
        dataset_id="deepcrack",
        sample_id="11289-1",
        image_path=img_p,
        annotation_path=None,
        annotation_type=AnnotationType.UNANNOTATED,
        source_split="train",
        group_id="11289",
        original_labels=["crack"],
        image_width=544,
        image_height=384,
        channels=3,
        metadata={"custom": "meta"},
        provenance=ProvenanceRecord(
            source_dataset="DeepCrack",
            source_archive="DeepCrack.zip",
            pipeline_version="1.0.0"
        )
    )
    assert sample.dataset_id == "deepcrack"
    assert sample.group_id == "11289"
    assert sample.annotation_type == AnnotationType.UNANNOTATED


def test_deepcrack_group_id_extraction():
    assert extract_deepcrack_group_id("11289-1") == "11289"
    assert extract_deepcrack_group_id("11289-10") == "11289"
    assert extract_deepcrack_group_id("asset_A-5") == "asset_A"
    assert extract_deepcrack_group_id("single_frame") == "single_frame"


def test_group_leakage_detection_raises_on_overlap(tmp_path: Path):
    img_p = tmp_path / "img.jpg"
    img_p.write_bytes(b"dummy")

    prov = ProvenanceRecord(source_dataset="test", pipeline_version="1.0.0")
    s1 = DatasetSample(dataset_id="d1", sample_id="s1", image_path=img_p, group_id="group_A", image_width=100, image_height=100, provenance=prov)
    s2 = DatasetSample(dataset_id="d1", sample_id="s2", image_path=img_p, group_id="group_A", image_width=100, image_height=100, provenance=prov)
    s3 = DatasetSample(dataset_id="d1", sample_id="s3", image_path=img_p, group_id="group_B", image_width=100, image_height=100, provenance=prov)

    # Overlapping group_A between train and val
    splits_with_leakage = {
        "train": [s1],
        "val": [s2],
        "test": [s3]
    }

    with pytest.raises(GroupLeakageError) as exc_info:
        validate_group_leakage(splits_with_leakage)
    assert "Group leakage detected" in str(exc_info.value)
    assert "group_A" in str(exc_info.value)


def test_group_leakage_detection_passes_on_disjoint_groups(tmp_path: Path):
    img_p = tmp_path / "img.jpg"
    img_p.write_bytes(b"dummy")

    prov = ProvenanceRecord(source_dataset="test", pipeline_version="1.0.0")
    s1 = DatasetSample(dataset_id="d1", sample_id="s1", image_path=img_p, group_id="group_A", image_width=100, image_height=100, provenance=prov)
    s2 = DatasetSample(dataset_id="d1", sample_id="s2", image_path=img_p, group_id="group_B", image_width=100, image_height=100, provenance=prov)
    s3 = DatasetSample(dataset_id="d1", sample_id="s3", image_path=img_p, group_id="group_C", image_width=100, image_height=100, provenance=prov)

    valid_splits = {
        "train": [s1],
        "val": [s2],
        "test": [s3]
    }
    # Should not raise
    validate_group_leakage(valid_splits)


def test_deterministic_group_splitter(tmp_path: Path):
    img_p = tmp_path / "img.jpg"
    img_p.write_bytes(b"dummy")
    prov = ProvenanceRecord(source_dataset="test", pipeline_version="1.0.0")

    samples = []
    for g_idx in range(10):
        for s_idx in range(3):
            samples.append(
                DatasetSample(
                    dataset_id="d1",
                    sample_id=f"g{g_idx}_{s_idx}",
                    image_path=img_p,
                    group_id=f"group_{g_idx}",
                    image_width=100,
                    image_height=100,
                    provenance=prov
                )
            )

    splitter_1 = DatasetSplitter(seed=42)
    splits_1 = splitter_1.split_samples(samples, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, group_aware=True)

    splitter_2 = DatasetSplitter(seed=42)
    splits_2 = splitter_2.split_samples(samples, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, group_aware=True)

    # Identical reproducible split mapping
    assert [s.sample_id for s in splits_1["train"]] == [s.sample_id for s in splits_2["train"]]
    assert [s.sample_id for s in splits_1["val"]] == [s.sample_id for s in splits_2["val"]]
    assert [s.sample_id for s in splits_1["test"]] == [s.sample_id for s in splits_2["test"]]

    # Zero group leakage
    validate_group_leakage(splits_1)


def test_nearest_neighbor_mask_resizer_preserves_discrete_values():
    # 4x4 binary mask with values 0 and 255
    orig_mask = [
        [0,   0,   255, 255],
        [0,   0,   255, 255],
        [255, 255, 0,   0],
        [255, 255, 0,   0],
    ]

    # Resize to 8x8
    resized_8x8 = nearest_neighbor_resize_2d(orig_mask, target_w=8, target_h=8)
    assert len(resized_8x8) == 8
    assert len(resized_8x8[0]) == 8

    # Ensure strictly discrete values
    unexpected = validate_binary_mask_discrete_values(resized_8x8, allowed_values=(0, 255))
    assert unexpected == []


def test_letterbox_mask_and_geometry():
    # 2x4 mask
    orig_mask = [
        [0, 255, 255, 0],
        [0, 255, 255, 0]
    ]
    canvas, geom = letterbox_mask_2d(orig_mask, target_w=8, target_h=8, pad_value=0)
    assert len(canvas) == 8
    assert len(canvas[0]) == 8
    assert geom.mode == ImageResizeMode.LETTERBOX
    assert geom.pad_y > 0 or geom.pad_x > 0

    # Ensure discrete values preserved
    assert validate_binary_mask_discrete_values(canvas, allowed_values=(0, 255)) == []


def test_discrete_mask_value_validator_detects_corrupted_values():
    corrupted_mask = [
        [0, 128, 255],
        [0, 42, 255]
    ]
    unexpected = validate_binary_mask_discrete_values(corrupted_mask, allowed_values=(0, 255))
    assert unexpected == [42, 128]


def test_augmentation_eval_safety():
    cfg = AugmentationConfig(enabled=False)
    assert cfg.is_eval_safe() is True

    pipeline = AugmentationPipeline(cfg)
    img_data = [[1, 2], [3, 4]]
    mask_data = [[0, 255], [255, 0]]

    # When not in training mode, augmentation must be a strict no-op
    out_img, out_mask, meta = pipeline.apply_to_sample(img_data, mask_data, is_training=False)
    assert out_img == img_data
    assert out_mask == mask_data
    assert meta["applied_transforms"] == []
