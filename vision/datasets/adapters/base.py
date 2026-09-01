"""Base abstract dataset adapter."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from vision.datasets.metadata import DatasetMetadata
from vision.datasets.sample import DatasetSample


class BaseDatasetAdapter(ABC):
    """Abstract interface for dataset adapters."""

    def __init__(self, raw_data_dir: Path):
        self.raw_data_dir = Path(raw_data_dir)

    @property
    @abstractmethod
    def dataset_id(self) -> str:
        """Returns the unique dataset identifier."""
        pass

    @abstractmethod
    def extract_metadata(self) -> DatasetMetadata:
        """Extracts dataset metadata schema."""
        pass

    @abstractmethod
    def discover_samples(self) -> List[DatasetSample]:
        """Discovers and parses all samples in the raw dataset."""
        pass

    @abstractmethod
    def validate_sample(self, sample: DatasetSample) -> List[str]:
        """Validates the sample and returns a list of error strings (empty if valid)."""
        pass

    @abstractmethod
    def compute_statistics(self, samples: List[DatasetSample]) -> Dict[str, Any]:
        """Calculates dataset summary statistics."""
        pass
