from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DatasetTaskType(str, Enum):
    OBJECT_DETECTION = "object_detection"
    INSTANCE_SEGMENTATION = "instance_segmentation"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    ANOMALY_DETECTION = "anomaly_detection"
    CLASSIFICATION = "classification"


class SourceResolution(BaseModel):
    """Resolution profile of the source dataset imagery."""
    min_width: Optional[int] = None
    min_height: Optional[int] = None
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    typical_resolution: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class DatasetSplitInfo(BaseModel):
    """Image count distribution across standard splits."""
    train_count: int = Field(default=0, ge=0)
    val_count: int = Field(default=0, ge=0)
    test_count: int = Field(default=0, ge=0)
    total_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class DatasetMetadata(BaseModel):
    """Typed metadata schema representing source and processed inspection datasets."""
    dataset_name: str = Field(..., description="Canonical dataset identifier")
    source: str = Field(..., description="Author, publishing institution, or primary DOI")
    version: str = Field(default="1.0.0", description="Dataset release version")
    license: str = Field(..., description="Dataset licensing terms (e.g., CC BY 4.0, CC BY-NC-SA 4.0)")
    annotation_format: str = Field(..., description="Native annotation structure (e.g., COCO, Pascal VOC, YOLO)")
    image_count: int = Field(..., ge=0, description="Total verified images in dataset")
    categories: List[str] = Field(..., description="List of source defect categories")
    splits: DatasetSplitInfo = Field(default_factory=DatasetSplitInfo, description="Split breakdown")
    resolution_info: Optional[SourceResolution] = Field(default=None, description="Image resolution range")
    intended_task: DatasetTaskType = Field(..., description="Primary ML task target")
    notes: Optional[str] = Field(default=None, description="Domain specific context or ingestion notes")

    model_config = ConfigDict(extra="forbid")
