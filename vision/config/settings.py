from typing import Tuple
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VisionSettings(BaseSettings):
    """Configuration settings for the Computer Vision subsystem."""

    VISION_MODEL_NAME: str = Field(
        default="pipeline-defect-yolov8",
        description="Identifier of the vision detection/segmentation model"
    )
    VISION_MODEL_VERSION: str = Field(
        default="0.1.0",
        description="Version tag for the active vision model"
    )
    VISION_DEVICE: str = Field(
        default="cpu",
        description="Compute device for inference ('cpu', 'cuda', 'mps')"
    )
    VISION_CONFIDENCE_THRESHOLD: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Minimum detection confidence threshold"
    )
    VISION_INPUT_SIZE: Tuple[int, int] = Field(
        default=(640, 640),
        description="Standard input dimensions (height, width) for preprocessing"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


vision_settings = VisionSettings()
