"""Dataset splitting infrastructure supporting both COCO datasets and normalized DatasetSample streams."""

import random
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple
from vision.datasets.coco import COCOAnnotation, COCODataset, COCOImage
from vision.datasets.leakage import validate_group_leakage
from vision.datasets.sample import DatasetSample


class DatasetSplitter:
    """Orchestrates deterministic, group-aware dataset partitioning across train, validation, and test splits."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def split_samples(
        self,
        samples: List[DatasetSample],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        group_aware: bool = True,
    ) -> Dict[str, List[DatasetSample]]:
        """
        Splits a list of DatasetSample instances deterministically into train, val, and test partitions.
        Ensures strict group atomicity when group_aware is True (zero group leakage).
        """
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Split ratios must sum to 1.0, got {total}")

        if not samples:
            return {"train": [], "val": [], "test": []}

        rng = random.Random(self.seed)

        if not group_aware:
            shuffled = list(samples)
            rng.shuffle(shuffled)
            n_total = len(shuffled)
            n_train = int(n_total * train_ratio)
            n_val = int(n_total * val_ratio)
            splits = {
                "train": shuffled[:n_train],
                "val": shuffled[n_train:n_train + n_val],
                "test": shuffled[n_train + n_val:]
            }
            return splits

        # Group-aware partitioning
        groups: Dict[str, List[DatasetSample]] = defaultdict(list)
        for s in samples:
            gid = s.group_id or s.sample_id
            groups[gid].append(s)

        group_keys = sorted(list(groups.keys()))
        rng.shuffle(group_keys)

        n_groups = len(group_keys)
        n_train_g = int(n_groups * train_ratio)
        n_val_g = int(n_groups * val_ratio)

        train_g_set = set(group_keys[:n_train_g])
        val_g_set = set(group_keys[n_train_g:n_train_g + n_val_g])
        test_g_set = set(group_keys[n_train_g + n_val_g:])

        splits: Dict[str, List[DatasetSample]] = {
            "train": [s for gid in train_g_set for s in groups[gid]],
            "val": [s for gid in val_g_set for s in groups[gid]],
            "test": [s for gid in test_g_set for s in groups[gid]],
        }

        # Validate zero leakage
        validate_group_leakage(splits)
        return splits

    def split_by_ratio(
        self,
        dataset: COCODataset,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
    ) -> Tuple[COCODataset, COCODataset, COCODataset]:
        """Performs a deterministic, random partition of a COCODataset by image."""
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Split ratios must sum to 1.0, got {total}")

        images = list(dataset.images)
        rng = random.Random(self.seed)
        rng.shuffle(images)

        n_total = len(images)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)

        train_imgs = images[:n_train]
        val_imgs = images[n_train:n_train + n_val]
        test_imgs = images[n_train + n_val:]

        return (
            self._create_subset(dataset, train_imgs, "train"),
            self._create_subset(dataset, val_imgs, "val"),
            self._create_subset(dataset, test_imgs, "test"),
        )

    def split_by_group(
        self,
        dataset: COCODataset,
        group_key: str = "asset_id",
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
    ) -> Tuple[COCODataset, COCODataset, COCODataset]:
        """Groups images by asset/pipe segment or session before partitioning to prevent data leakage."""
        groups: Dict[str, List[COCOImage]] = {}
        ungrouped: List[COCOImage] = []

        for img in dataset.images:
            val = getattr(img, group_key, None)
            if val:
                groups.setdefault(str(val), []).append(img)
            else:
                ungrouped.append(img)

        group_names = sorted(list(groups.keys()))
        rng = random.Random(self.seed)
        rng.shuffle(group_names)

        n_groups = len(group_names)
        n_train_g = int(n_groups * train_ratio)
        n_val_g = int(n_groups * val_ratio)

        train_groups = set(group_names[:n_train_g])
        val_groups = set(group_names[n_train_g:n_train_g + n_val_g])
        test_groups = set(group_names[n_train_g + n_val_g:])

        train_imgs: List[COCOImage] = []
        val_imgs: List[COCOImage] = []
        test_imgs: List[COCOImage] = []

        for g_name, g_images in groups.items():
            if g_name in train_groups:
                train_imgs.extend(g_images)
            elif g_name in val_groups:
                val_imgs.extend(g_images)
            else:
                test_imgs.extend(g_images)

        # Distribute ungrouped images
        if ungrouped:
            rng.shuffle(ungrouped)
            n_un = len(ungrouped)
            n_u_train = int(n_un * train_ratio)
            n_u_val = int(n_un * val_ratio)
            train_imgs.extend(ungrouped[:n_u_train])
            val_imgs.extend(ungrouped[n_u_train:n_u_train + n_u_val])
            test_imgs.extend(ungrouped[n_u_train + n_u_val:])

        return (
            self._create_subset(dataset, train_imgs, "train"),
            self._create_subset(dataset, val_imgs, "val"),
            self._create_subset(dataset, test_imgs, "test"),
        )

    @staticmethod
    def _create_subset(
        source_dataset: COCODataset,
        subset_images: List[COCOImage],
        split_name: str,
    ) -> COCODataset:
        img_ids = {img.id for img in subset_images}
        subset_annotations = [
            ann for ann in source_dataset.annotations if ann.image_id in img_ids
        ]

        return COCODataset(
            info={
                **source_dataset.info,
                "description": f"{source_dataset.info.get('description', '')} ({split_name})",
            },
            licenses=source_dataset.licenses,
            images=subset_images,
            annotations=subset_annotations,
            categories=source_dataset.categories,
        )
