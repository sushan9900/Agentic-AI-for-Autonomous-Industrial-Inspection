from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator


class COCOCategory(BaseModel):
    """COCO standard category descriptor."""
    id: int = Field(..., ge=0, description="Unique integer category ID")
    name: str = Field(..., description="Category label name")
    supercategory: Optional[str] = Field(default="defect", description="Supercategory grouping")

    model_config = ConfigDict(extra="allow")


class COCOImage(BaseModel):
    """COCO standard image record."""
    id: int = Field(..., ge=0, description="Unique integer image ID")
    file_name: str = Field(..., description="Image filename or relative path")
    width: int = Field(..., gt=0, description="Image pixel width")
    height: int = Field(..., gt=0, description="Image pixel height")
    source_dataset: Optional[str] = Field(default=None, description="Originating dataset identifier")
    asset_id: Optional[str] = Field(default=None, description="Asset or pipe section identifier for grouping")
    session_id: Optional[str] = Field(default=None, description="Inspection run session identifier")

    model_config = ConfigDict(extra="allow")


class COCOAnnotation(BaseModel):
    """COCO standard annotation record supporting bounding boxes and polygon segmentation."""
    id: int = Field(..., ge=0, description="Unique integer annotation ID")
    image_id: int = Field(..., ge=0, description="Associated image ID")
    category_id: int = Field(..., ge=0, description="Associated category ID")
    bbox: List[float] = Field(
        ...,
        description="Bounding box in [x_min, y_min, width, height] pixel coordinates"
    )
    area: float = Field(..., ge=0.0, description="Area of bounding box or segmentation mask")
    segmentation: Union[List[List[float]], Dict[str, Any]] = Field(
        default_factory=list,
        description="Polygon coordinates [[x1, y1, x2, y2, ...]] or RLE dict"
    )
    iscrowd: int = Field(default=0, ge=0, le=1, description="0 for individual polygon, 1 for RLE")

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_bbox_structure(self) -> "COCOAnnotation":
        if len(self.bbox) != 4:
            raise ValueError(f"COCO bbox must contain exactly 4 values [x, y, w, h], got {self.bbox}")
        x, y, w, h = self.bbox
        if w < 0 or h < 0:
            raise ValueError(f"COCO bbox width and height must be non-negative, got w={w}, h={h}")
        return self


class COCODataset(BaseModel):
    """Master COCO format dataset schema."""
    info: Dict[str, Any] = Field(
        default_factory=lambda: {
            "description": "Agentic Industrial Inspection Master Dataset",
            "version": "1.0",
            "year": 2026,
        }
    )
    licenses: List[Dict[str, Any]] = Field(default_factory=list)
    images: List[COCOImage] = Field(default_factory=list)
    annotations: List[COCOAnnotation] = Field(default_factory=list)
    categories: List[COCOCategory] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")
