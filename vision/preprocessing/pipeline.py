from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
import os


class PreprocessingError(Exception):
    """Exception raised for errors during input preprocessing."""
    pass


class InvalidImageInputError(PreprocessingError):
    """Raised when the input image path or data payload fails validation."""
    pass


class BasePreprocessor(ABC):
    """Abstract interface for image preprocessing pipelines."""

    @abstractmethod
    def validate(self, image_input: Union[str, bytes, Any]) -> bool:
        """Validates that the input image path or buffer exists and is valid."""
        pass

    @abstractmethod
    def preprocess(self, image_input: Union[str, bytes, Any]) -> Dict[str, Any]:
        """Applies validation, resizing, and normalization transformations."""
        pass


class ImagePreprocessor(BasePreprocessor):
    """Standard image preprocessing pipeline for industrial inspection imagery.
    
    Supports file path validation, resolution checks, and transformation parameter configuration.
    """

    def __init__(
        self,
        target_size: Tuple[int, int] = (640, 640),
        normalize: bool = True,
        mean: Optional[List[float]] = None,
        std: Optional[List[float]] = None,
    ) -> None:
        self.target_size = target_size
        self.normalize = normalize
        self.mean = mean or [0.485, 0.456, 0.406]
        self.std = std or [0.229, 0.224, 0.225]

    def validate(self, image_input: Union[str, bytes, Any]) -> bool:
        """Performs initial integrity checks on the image input.
        
        Args:
            image_input: File path string, raw byte buffer, or image object.
            
        Returns:
            True if input passes structural validation.
            
        Raises:
            InvalidImageInputError: If file is missing, empty, or format is unsupported.
        """
        if image_input is None:
            raise InvalidImageInputError("Image input cannot be None.")

        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise InvalidImageInputError(f"Image file does not exist: {image_input}")
            
            valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
            _, ext = os.path.splitext(image_input.lower())
            if ext not in valid_extensions:
                raise InvalidImageInputError(
                    f"Unsupported image extension '{ext}'. Valid extensions: {valid_extensions}"
                )
            
            if os.path.getsize(image_input) == 0:
                raise InvalidImageInputError(f"Image file is empty (0 bytes): {image_input}")

        elif isinstance(image_input, bytes):
            if len(image_input) == 0:
                raise InvalidImageInputError("Image byte buffer is empty.")
        
        return True

    def preprocess(self, image_input: Union[str, bytes, Any]) -> Dict[str, Any]:
        """Prepares the validated image input for inference.
        
        Returns a structured dictionary containing normalized metadata and parameters
        ready to be passed to concrete model backends.
        """
        self.validate(image_input)

        return {
            "source": image_input,
            "target_size": self.target_size,
            "normalized": self.normalize,
            "mean": self.mean,
            "std": self.std,
        }
