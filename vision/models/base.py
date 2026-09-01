from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class VisionModelError(Exception):
    """Base exception for vision model operations."""
    pass


class ModelNotConfiguredError(VisionModelError):
    """Raised when an inference operation is requested without a loaded/configured model."""
    pass


class ModelInferenceError(VisionModelError):
    """Raised when model inference execution fails."""
    pass


class BaseVisionModel(ABC):
    """Abstract Base Class for Computer Vision models.
    
    This abstraction allows different model architectures (e.g., YOLOv8, YOLO11,
    SegFormer, PatchCore) to be swapped without modifying the inference pipeline.
    """

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu") -> None:
        self.model_path = model_path
        self.device = device
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        """Indicates whether model weights/backends are loaded in memory."""
        return self._is_loaded

    @abstractmethod
    def load(self) -> None:
        """Loads model weights, graph, or runtime engine into target device memory."""
        pass

    @abstractmethod
    def predict(self, preprocessed_input: Any) -> Any:
        """Executes forward inference on preprocessed tensor/input data.
        
        Args:
            preprocessed_input: Standardized preprocessed input format.
            
        Returns:
            Raw model predictions (e.g., bounding boxes, logits, masks).
            
        Raises:
            ModelNotConfiguredError: If model weights are not loaded.
            ModelInferenceError: If forward pass execution fails.
        """
        pass

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Returns model specification metadata (e.g., name, version, class mapping)."""
        pass
