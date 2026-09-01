from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates for a detected defect."""
    x: float = Field(..., ge=0.0, description="Top-left X coordinate or normalized center X")
    y: float = Field(..., ge=0.0, description="Top-left Y coordinate or normalized center Y")
    width: float = Field(..., ge=0.0, description="Width of the bounding box")
    height: float = Field(..., ge=0.0, description="Height of the bounding box")

    model_config = ConfigDict(extra="forbid")


class SeverityFeatures(BaseModel):
    """Extensible visual severity indicators extracted during CV inspection."""
    affected_area_percentage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Estimated percentage of component surface affected"
    )
    location_type: Optional[str] = Field(
        default=None,
        description="Location context (e.g., weld_seam, pipe_body, joint, flange)"
    )
    estimated_size: Optional[str] = Field(
        default=None,
        description="Estimated physical dimensions (e.g., '12cm x 3cm')"
    )
    spread: Optional[str] = Field(
        default=None,
        description="Pattern/spread description (e.g., localized, longitudinal, circumferential)"
    )
    visual_severity: Optional[str] = Field(
        default=None,
        description="Visual severity indicator (e.g., low, moderate, severe, critical)"
    )

    model_config = ConfigDict(extra="allow")


class Detection(BaseModel):
    """Individual defect detection record produced by the vision model."""
    defect_id: str = Field(..., description="Unique identifier for the detected defect instance")
    defect_type: str = Field(..., description="Classification category (e.g., corrosion, crack, deformation)")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence score between 0.0 and 1.0"
    )
    bounding_box: BoundingBox = Field(..., description="Spatial bounding coordinates")
    mask_reference: Optional[str] = Field(
        default=None,
        description="Optional URI or identifier for segmentation mask binary/RLE"
    )
    severity_features: Optional[SeverityFeatures] = Field(
        default=None,
        description="Extensible visual features characterizing defect severity"
    )

    model_config = ConfigDict(extra="forbid")


class ProcessingMetadata(BaseModel):
    """Execution metadata and performance indicators for an inspection run."""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when processing occurred"
    )
    execution_time_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total preprocessing and inference latency in milliseconds"
    )
    device: Optional[str] = Field(
        default=None,
        description="Device on which inference executed (e.g., 'cpu', 'cuda:0')"
    )
    input_resolution: Optional[List[int]] = Field(
        default=None,
        description="Input dimensions [height, width, channels]"
    )
    additional_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary additional processing diagnostics"
    )

    model_config = ConfigDict(extra="allow")


class InspectionResult(BaseModel):
    """Normalized structured inspection output produced by the Computer Vision subsystem.
    
    This contract serves as the decoupling interface consumed by the downstream Agentic AI layer.
    """
    inspection_id: str = Field(..., description="Unique inspection transaction identifier")
    component_id: str = Field(..., description="Identifier of the industrial component inspected")
    component_type: str = Field(..., description="Type/category of the component (e.g., pipeline, vessel)")
    image_id: str = Field(..., description="Source inspection image identifier or path reference")
    model_name: str = Field(..., description="Identifier of the vision model used for detection")
    model_version: str = Field(..., description="Version tag of the vision model")
    detections: List[Detection] = Field(
        default_factory=list,
        description="List of detected defect anomalies"
    )
    processing_metadata: ProcessingMetadata = Field(
        default_factory=ProcessingMetadata,
        description="Operational metadata and latency measurements"
    )

    model_config = ConfigDict(extra="forbid")
