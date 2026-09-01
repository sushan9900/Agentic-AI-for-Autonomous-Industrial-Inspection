"""Dataset adapter package initialization."""

from vision.datasets.adapters.base import BaseDatasetAdapter
from vision.datasets.adapters.deepcrack import DeepCrackAdapter
from vision.datasets.adapters.corrosion_detection import CorrosionDetectionAdapter
from vision.datasets.adapters.corrosion_segmentation import CorrosionSegmentationAdapter

__all__ = [
    "BaseDatasetAdapter",
    "DeepCrackAdapter",
    "CorrosionDetectionAdapter",
    "CorrosionSegmentationAdapter",
]
