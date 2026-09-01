"""Versioned Vision-to-Agent Evidence Contract (Schema v1.0).

This schema is the authoritative, versioned, project-owned evidence contract
consumed by the downstream Agentic AI reasoning layer.
"""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from vision.schemas.inspection import SeverityFeatures


class InspectionStatus(str, Enum):
    """Normalized status of the vision inspection run."""
    SUCCESS = "SUCCESS"                      # Defect(s) detected with high confidence
    NO_DETECTIONS = "NO_DETECTIONS"          # Clean image; no defects detected above threshold
    QUALITY_WARNING = "QUALITY_WARNING"      # Inspection executed, but image quality degraded
    FAILED = "FAILED"                        # Model or pipeline execution error


class QualityWarningType(str, Enum):
    """Specific image quality impairment warnings."""
    LOW_RESOLUTION = "LOW_RESOLUTION"
    BLUR = "BLUR"
    LOW_CONTRAST = "LOW_CONTRAST"
    OVEREXPOSURE = "OVEREXPOSURE"
    UNDEREXPOSURE = "UNDEREXPOSURE"


class SourceImageProvenance(BaseModel):
    """Cryptographic and physical provenance of the inspected image."""
    filename: str = Field(..., description="Image filename or relative path")
    file_extension: str = Field(..., description="File extension (e.g. '.jpg', '.png')")
    width: int = Field(..., ge=1, description="Image width in pixels")
    height: int = Field(..., ge=1, description="Image height in pixels")
    channels: int = Field(default=3, ge=1, le=4, description="Number of color channels")
    file_size_bytes: int = Field(..., ge=0, description="Image file size on disk")
    sha256_hash: str = Field(..., description="SHA-256 digest of source image content")

    model_config = ConfigDict(extra="forbid")


class ModelProvenance(BaseModel):
    """Detailed model architecture, runtime, and checkpoint provenance."""
    model_name: str = Field(..., description="Canonical model identifier (e.g. 'YOLO11n-seg')")
    model_architecture: str = Field(..., description="Model architecture type")
    model_version: str = Field(default="1.0.0", description="Model release version")
    checkpoint_identifier: str = Field(..., description="Checkpoint filename or relative path")
    checkpoint_sha256: str = Field(..., description="SHA-256 digest of model checkpoint file")
    framework: str = Field(default="ultralytics", description="Underlying ML framework")
    framework_version: str = Field(..., description="Framework release version")
    confidence_threshold: float = Field(..., ge=0.0, le=1.0, description="Confidence filter applied")
    input_size: List[int] = Field(default_factory=lambda: [640, 640], description="Inference input tensor dimensions [H, W]")
    device: str = Field(..., description="Target compute device (e.g. 'cuda:0', 'cpu')")

    model_config = ConfigDict(extra="forbid")


class NormalizedBoundingBox(BaseModel):
    """Dual-coordinate bounding box representation (pixel and normalized)."""
    # Pixel coordinates
    x_pixel: float = Field(..., ge=0.0, description="Top-left X coordinate in pixels")
    y_pixel: float = Field(..., ge=0.0, description="Top-left Y coordinate in pixels")
    width_pixel: float = Field(..., ge=0.0, description="Width in pixels")
    height_pixel: float = Field(..., ge=0.0, description="Height in pixels")
    # Normalized coordinates [0.0, 1.0]
    x_norm: float = Field(..., ge=0.0, le=1.0, description="Normalized top-left X")
    y_norm: float = Field(..., ge=0.0, le=1.0, description="Normalized top-left Y")
    width_norm: float = Field(..., ge=0.0, le=1.0, description="Normalized box width")
    height_norm: float = Field(..., ge=0.0, le=1.0, description="Normalized box height")

    model_config = ConfigDict(extra="forbid")


class SegmentationEvidence(BaseModel):
    """Lightweight structured segmentation metadata without heavy raw binary payloads."""
    polygon_count: int = Field(default=0, ge=0, description="Number of distinct polygon contours")
    normalized_polygons: List[List[float]] = Field(
        default_factory=list,
        description="Flattened [x1, y1, x2, y2, ...] normalized polygon vertices"
    )
    mask_area_pixels: float = Field(default=0.0, ge=0.0, description="Total mask area in pixels")
    mask_area_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of surface covered")
    mask_artifact_path: Optional[str] = Field(None, description="Relative path to standalone mask artifact file if saved")

    model_config = ConfigDict(extra="forbid")


class DetectionEvidence(BaseModel):
    """Deterministic, individual defect detection record."""
    detection_id: str = Field(..., description="Deterministic detection identifier (e.g. 'det-001')")
    class_id: int = Field(default=0, ge=0, description="Taxonomy integer class ID")
    defect_type: str = Field(..., description="Canonical defect category name (e.g. 'crack')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")
    bounding_box: NormalizedBoundingBox = Field(..., description="Spatial bounding coordinates")
    segmentation: Optional[SegmentationEvidence] = Field(None, description="Structured segmentation evidence")
    severity_features: SeverityFeatures = Field(..., description="Deterministic measurable visual features")

    model_config = ConfigDict(extra="forbid")


class DetectionSummary(BaseModel):
    """Summary statistics for detections in an inspection event."""
    detection_count: int = Field(..., ge=0, description="Total defects detected above threshold")
    max_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Highest confidence detection score")
    mean_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average confidence score")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Lowest confidence detection score")

    model_config = ConfigDict(extra="forbid")


class QualityAssessment(BaseModel):
    """Deterministic, measurable image quality metrics."""
    brightness_mean: float = Field(..., ge=0.0, le=255.0, description="Mean grayscale intensity [0, 255]")
    contrast_std: float = Field(..., ge=0.0, description="Standard deviation of grayscale intensity")
    blur_score: float = Field(..., ge=0.0, description="Variance of the Laplacian (higher is sharper)")
    blur_detected: bool = Field(default=False, description="True if blur score is below critical threshold")
    low_contrast_detected: bool = Field(default=False, description="True if contrast std is below threshold")
    underexposed: bool = Field(default=False, description="True if brightness is critically low")
    overexposed: bool = Field(default=False, description="True if brightness is saturated")
    warnings: List[QualityWarningType] = Field(default_factory=list, description="List of quality warnings")

    model_config = ConfigDict(extra="forbid")


class ProcessingTrace(BaseModel):
    """Monotonic execution timing breakdown across all pipeline stages."""
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validation_ms: float = Field(..., ge=0.0, description="Image validation latency in ms")
    preprocessing_ms: float = Field(..., ge=0.0, description="Image preprocessing latency in ms")
    inference_ms: float = Field(..., ge=0.0, description="Model forward pass latency in ms")
    postprocessing_ms: float = Field(..., ge=0.0, description="Prediction parsing latency in ms")
    evidence_construction_ms: float = Field(..., ge=0.0, description="Evidence structuring latency in ms")
    total_execution_ms: float = Field(..., ge=0.0, description="Total end-to-end latency in ms")

    model_config = ConfigDict(extra="forbid")


class VisionEvidence(BaseModel):
    """Authoritative, versioned Vision-to-Agent Evidence Contract."""
    schema_version: str = Field(default="1.0", description="Evidence contract schema specification version")
    inspection_id: str = Field(..., description="Unique deterministic inspection transaction identifier")
    component_id: str = Field(..., description="Asset or industrial component identifier")
    component_type: str = Field(default="pipeline", description="Category of inspected physical component")
    status: InspectionStatus = Field(..., description="Operational status of inspection result")
    source_image: SourceImageProvenance = Field(..., description="Source image metadata and SHA-256 hash")
    model: ModelProvenance = Field(..., description="Model architecture, checkpoint hash, and runtime")
    summary: DetectionSummary = Field(..., description="Summary statistics of detections")
    detections: List[DetectionEvidence] = Field(default_factory=list, description="Deterministic list of detected defects")
    quality: QualityAssessment = Field(..., description="Objective image quality diagnostics")
    processing: ProcessingTrace = Field(..., description="Monotonic execution timing breakdown")

    model_config = ConfigDict(extra="forbid")
