"""Group leakage detection and duplicate content analysis."""

import hashlib
from collections import defaultdict
from typing import Dict, List, Set
from vision.datasets.sample import DatasetSample


class GroupLeakageError(ValueError):
    """Raised when group-based leakage is detected across dataset splits."""
    pass


def validate_group_leakage(splits: Dict[str, List[DatasetSample]]) -> None:
    """
    Validates that no asset group ID crosses split boundaries.
    
    Raises:
        GroupLeakageError: If any group_id appears in multiple splits.
    """
    split_groups: Dict[str, Set[str]] = {}
    for split_name, samples in splits.items():
        groups = {s.group_id for s in samples if s.group_id}
        split_groups[split_name] = groups

    split_names = list(splits.keys())
    for i in range(len(split_names)):
        for j in range(i + 1, len(split_names)):
            s1, s2 = split_names[i], split_names[j]
            overlap = split_groups[s1].intersection(split_groups[s2])
            if overlap:
                raise GroupLeakageError(
                    f"Group leakage detected between '{s1}' and '{s2}' splits! "
                    f"Overlapping group IDs ({len(overlap)}): {sorted(list(overlap))[:10]}"
                )


def detect_duplicate_hashes(samples: List[DatasetSample]) -> Dict[str, List[str]]:
    """
    Detects identical image contents via SHA-256 hashing.
    Returns mapping of SHA-256 hash -> list of sample_ids with identical content.
    """
    hash_to_samples: Dict[str, List[str]] = defaultdict(list)
    for sample in samples:
        if not sample.image_path.exists():
            continue
        h = hashlib.sha256()
        with open(sample.image_path, "rb") as f:
            while chunk := f.read(512 * 1024):
                h.update(chunk)
        digest = h.hexdigest()
        hash_to_samples[digest].append(sample.sample_id)

    # Filter only duplicates
    return {h: s_ids for h, s_ids in hash_to_samples.items() if len(s_ids) > 1}
