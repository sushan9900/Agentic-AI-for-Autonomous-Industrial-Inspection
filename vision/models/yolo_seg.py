"""Ultralytics YOLO11-Seg concrete implementation of BaseVisionModel."""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from vision.inference.severity import extract_severity_features
from vision.models.base import BaseVisionModel, ModelInferenceError, ModelNotConfiguredError
from vision.schemas.inspection import BoundingBox, Detection, SeverityFeatures


class YOLOSegmentationModel(BaseVisionModel):
    """Encapsulated YOLO11-Seg model wrapper implementing BaseVisionModel."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        device: str = "cpu",
        confidence_threshold: float = 0.25
    ) -> None:
        super().__init__(model_path=str(model_path) if model_path else None, device=device)
        self.confidence_threshold = confidence_threshold
        self._model = None
        self._class_names = {0: "crack"}

    def load(self) -> None:
        """Loads YOLO weights into target device memory."""
        if not self.model_path or not Path(self.model_path).exists():
            raise ModelNotConfiguredError(f"Model checkpoint not found at: {self.model_path}")

        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
            if hasattr(self._model, "names") and self._model.names:
                self._class_names = self._model.names
            self._is_loaded = True
        except Exception as e:
            raise ModelInferenceError(f"Failed to load YOLO model: {e}") from e

    def predict(
        self,
        preprocessed_input: Any,
        confidence_threshold: Optional[float] = None
    ) -> List[Detection]:
        """
        Executes segmentation inference and translates predictions into standardized Detection contracts.
        """
        if not self._is_loaded or self._model is None:
            raise ModelNotConfiguredError("Cannot run inference; model weights are not loaded.")

        conf = confidence_threshold if confidence_threshold is not None else self.confidence_threshold

        try:
            results = self._model.predict(
                source=preprocessed_input,
                conf=conf,
                device=self.device,
                verbose=False
            )
        except Exception as e:
            raise ModelInferenceError(f"YOLO inference execution failed: {e}") from e

        detections: List[Detection] = []
        if not results:
            return detections

        res = results[0]  # First image in batch
        orig_img_shape = res.orig_shape  # (h, w)
        img_h, img_w = int(orig_img_shape[0]), int(orig_img_shape[1])

        boxes = res.boxes
        masks = res.masks

        if boxes is None or len(boxes) == 0:
            return detections

        n_instances = len(boxes)
        for i in range(n_instances):
            # Extract box coordinates (xyxy in pixels)
            xyxy = boxes.xyxy[i].cpu().numpy().tolist()
            score = float(boxes.conf[i].cpu().item())
            cls_id = int(boxes.cls[i].cpu().item())
            defect_label = self._class_names.get(cls_id, "crack")

            x_min = max(0.0, float(xyxy[0]))
            y_min = max(0.0, float(xyxy[1]))
            x_max = min(float(img_w), float(xyxy[2]))
            y_max = min(float(img_h), float(xyxy[3]))
            width = max(0.0, x_max - x_min)
            height = max(0.0, y_max - y_min)

            bbox = BoundingBox(
                x=round(x_min, 2),
                y=round(y_min, 2),
                width=round(width, 2),
                height=round(height, 2)
            )

            # Extract polygon points if mask is available
            polygon_pts: Optional[List[List[float]]] = None
            if masks is not None and len(masks.xyn) > i:
                poly_arr = masks.xyn[i]
                if len(poly_arr) >= 3:
                    polygon_pts = poly_arr.tolist()

            # Extract measurable severity features
            severity = extract_severity_features(
                bbox=bbox,
                img_w=img_w,
                img_h=img_h,
                polygon_points=polygon_pts
            )

            det = Detection(
                defect_id=f"det_{uuid.uuid4().hex[:8]}",
                defect_type=defect_label,
                confidence=round(score, 4),
                bounding_box=bbox,
                severity_features=severity
            )
            detections.append(det)

        return detections

    def metadata(self) -> Dict[str, Any]:
        """Returns model specification metadata."""
        return {
            "model_type": "YOLO11n-seg",
            "task": "instance_segmentation",
            "model_path": self.model_path,
            "device": self.device,
            "is_loaded": self._is_loaded,
            "class_names": self._class_names,
            "confidence_threshold": self.confidence_threshold
        }
