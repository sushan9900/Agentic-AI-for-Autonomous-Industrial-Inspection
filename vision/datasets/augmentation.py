"""Augmentation configuration interface for synchronized image + mask transformations."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AugmentationConfig(BaseModel):
    """Configuration for data augmentation pipelines."""
    enabled: bool = Field(default=False, description="Whether augmentation is enabled (strictly disabled on eval splits)")
    horizontal_flip: bool = Field(default=True, description="Enable random horizontal flipping")
    horizontal_flip_prob: float = Field(default=0.5, ge=0.0, le=1.0)
    vertical_flip: bool = Field(default=True, description="Enable random vertical flipping")
    vertical_flip_prob: float = Field(default=0.5, ge=0.0, le=1.0)
    rotation_90: bool = Field(default=True, description="Enable 90-degree orthogonal rotations")
    rotation_90_prob: float = Field(default=0.5, ge=0.0, le=1.0)
    brightness_contrast: bool = Field(default=False, description="Enable photometric brightness and contrast jitter")
    gaussian_blur: bool = Field(default=False, description="Enable random Gaussian blurring")
    crop_scale_min: float = Field(default=0.8, ge=0.1, le=1.0, description="Minimum random crop scale")
    crop_scale_max: float = Field(default=1.0, ge=1.0, le=1.5, description="Maximum random crop scale")

    def is_eval_safe(self) -> bool:
        """Verifies that evaluation data is never modified by augmentation."""
        return not self.enabled


class AugmentationPipeline:
    """Synchronized image and segmentation mask augmentation orchestrator."""

    def __init__(self, config: Optional[AugmentationConfig] = None):
        self.config = config or AugmentationConfig(enabled=False)

    def apply_to_sample(
        self,
        image_data: Any,
        mask_data: Optional[Any] = None,
        is_training: bool = False
    ) -> tuple[Any, Optional[Any], Dict[str, Any]]:
        """
        Applies synchronized transformations to image and optional mask.
        Strict no-op when is_training is False or augmentation is disabled.
        """
        if not is_training or not self.config.enabled:
            return image_data, mask_data, {"applied_transforms": []}

        applied = []
        # Transformation execution hooks will be attached during model training phase
        return image_data, mask_data, {"applied_transforms": applied}
