"""Deterministic computer vision image quality assessment."""

from pathlib import Path
from typing import Any, List, Union
import cv2
import numpy as np
from vision.schemas.evidence import QualityAssessment, QualityWarningType


def assess_image_quality(
    image_input: Union[str, Path, np.ndarray],
    blur_threshold: float = 50.0,
    low_contrast_threshold: float = 20.0,
    underexposed_threshold: float = 35.0,
    overexposed_threshold: float = 220.0,
    min_resolution: int = 256
) -> QualityAssessment:
    """
    Performs deterministic image quality assessment on grayscale/RGB images.
    
    Metrics:
    - Blur Score: Variance of the Laplacian filter (higher = sharper, lower = blurrier)
    - Brightness Mean: Average pixel intensity across image [0, 255]
    - Contrast Std: Standard deviation of pixel intensities
    """
    if isinstance(image_input, (str, Path)):
        img = cv2.imread(str(image_input))
        if img is None:
            raise ValueError(f"Unable to read image for quality assessment: {image_input}")
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        raise TypeError(f"Unsupported image type for quality assessment: {type(image_input)}")

    h, w = img.shape[:2]

    # Convert to grayscale if color
    if len(img.shape) == 3 and img.shape[2] == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif len(img.shape) == 3 and img.shape[2] == 4:
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    else:
        gray = img

    # 1. Blur Score (Laplacian variance)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = float(laplacian.var())
    blur_detected = blur_score < blur_threshold

    # 2. Brightness & Contrast
    mean_val = float(np.mean(gray))
    std_val = float(np.std(gray))

    low_contrast = std_val < low_contrast_threshold
    underexposed = mean_val < underexposed_threshold
    overexposed = mean_val > overexposed_threshold

    # 3. Assemble warnings
    warnings: List[QualityWarningType] = []
    if min(w, h) < min_resolution:
        warnings.append(QualityWarningType.LOW_RESOLUTION)
    if blur_detected:
        warnings.append(QualityWarningType.BLUR)
    if low_contrast:
        warnings.append(QualityWarningType.LOW_CONTRAST)
    if underexposed:
        warnings.append(QualityWarningType.UNDEREXPOSURE)
    if overexposed:
        warnings.append(QualityWarningType.OVEREXPOSURE)

    return QualityAssessment(
        brightness_mean=round(mean_val, 2),
        contrast_std=round(std_val, 2),
        blur_score=round(blur_score, 2),
        blur_detected=blur_detected,
        low_contrast_detected=low_contrast,
        underexposed=underexposed,
        overexposed=overexposed,
        warnings=warnings
    )
