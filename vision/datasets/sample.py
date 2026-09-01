"""Dataset sample contract and normalized internal representation."""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnnotationType(str, Enum):
    """Normalized annotation type classification."""
    SEMANTIC_MASK = "semantic_mask"
    PATCH_ROI = "patch_roi"
    BOUNDING_BOX = "bounding_box"
    INSTANCE_POLYGON = "instance_polygon"
    UNANNOTATED = "unannotated"


class ProvenanceRecord(BaseModel):
    """Traceability provenance record for dataset samples."""
    source_dataset: str
    source_archive: Optional[str] = None
    source_archive_hash: Optional[str] = None
    pipeline_version: str = "1.0.0"
    processed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    transformation_applied: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DatasetSample(BaseModel):
    """Normalized internal sample representation across all industrial inspection datasets."""
    dataset_id: str = Field(..., description="Unique dataset identifier (e.g. 'deepcrack', 'corrosion_detection')")
    sample_id: str = Field(..., description="Unique sample identifier (e.g. '11289-1')")
    image_path: Path = Field(..., description="Path to RGB/grayscale image file")
    annotation_path: Optional[Path] = Field(None, description="Path to ground truth annotation file if available")
    annotation_type: AnnotationType = Field(default=AnnotationType.UNANNOTATED, description="Type of ground truth annotation")
    source_split: Optional[str] = Field(None, description="Original source split ('train', 'test', etc.) if provided")
    group_id: str = Field(..., description="Asset or structural parent group identifier to prevent split leakage")
    original_labels: List[str] = Field(default_factory=list, description="Original dataset class labels")
    image_width: int = Field(..., ge=1, description="Width of the image in pixels")
    image_height: int = Field(..., ge=1, description="Height of the image in pixels")
    channels: int = Field(default=3, ge=1, le=4, description="Number of color channels (1=Grayscale, 3=RGB, 4=RGBA)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dataset-specific additional metadata")
    provenance: ProvenanceRecord = Field(..., description="Traceability provenance information")

    model_config = ConfigDict(arbitrary_types_allowed=True)
