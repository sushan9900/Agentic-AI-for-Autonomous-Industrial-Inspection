"""End-to-end vision inspection inference pipeline orchestrator."""

import time
from typing import Any, Dict, List, Optional, Union
from vision.config.settings import vision_settings
from vision.inference.evidence_builder import EvidenceBuilder
from vision.models.base import BaseVisionModel, ModelNotConfiguredError
from vision.preprocessing.pipeline import BasePreprocessor, ImagePreprocessor
from vision.schemas.evidence import ProcessingTrace, VisionEvidence
from vision.schemas.inspection import Detection, InspectionResult, ProcessingMetadata


class InferencePipeline:
    """Coordinates input validation, preprocessing, model execution, post-processing,
    and packaging into standard InspectionResult and VisionEvidence schemas.
    """

    def __init__(
        self,
        model: Optional[BaseVisionModel] = None,
        preprocessor: Optional[BasePreprocessor] = None,
    ) -> None:
        self.model = model
        self.preprocessor = preprocessor or ImagePreprocessor(
            target_size=vision_settings.VISION_INPUT_SIZE
        )

    def set_model(self, model: BaseVisionModel) -> None:
        """Configures the active vision model backend."""
        self.model = model

    def run_inspection(
        self,
        image_input: Union[str, bytes, Any],
        inspection_id: str,
        component_id: str,
        component_type: str = "pipeline",
        image_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> InspectionResult:
        """Executes the inspection pipeline returning standard InspectionResult."""
        t_total_start = time.perf_counter()

        # Step 1: Validate & Preprocess
        t_prep_start = time.perf_counter()
        preprocessed_data = self.preprocessor.preprocess(image_input)
        prep_latency = (time.perf_counter() - t_prep_start) * 1000.0

        # Step 2: Model Inference Check
        if self.model is None or not self.model.is_loaded:
            raise ModelNotConfiguredError(
                "Inference cannot proceed: No vision model backend is configured or loaded in memory. "
                "Register and load a concrete BaseVisionModel implementation before running inspection."
            )

        # Step 3: Execute forward pass
        t_inf_start = time.perf_counter()
        if hasattr(self.model, "predict"):
            try:
                raw_predictions = self.model.predict(
                    image_input if isinstance(image_input, (str, bytes)) else preprocessed_data,
                    confidence_threshold=confidence_threshold
                )
            except TypeError:
                raw_predictions = self.model.predict(preprocessed_data)
        else:
            raw_predictions = []
        inf_latency = (time.perf_counter() - t_inf_start) * 1000.0

        # Step 4: Post-processing into detections
        t_post_start = time.perf_counter()
        model_meta = self.model.metadata()
        if isinstance(raw_predictions, list) and all(isinstance(d, Detection) for d in raw_predictions):
            detections = raw_predictions
        else:
            detections = self._post_process(raw_predictions)
        post_latency = (time.perf_counter() - t_post_start) * 1000.0

        execution_latency = (time.perf_counter() - t_total_start) * 1000.0

        # Step 5: Construct InspectionResult
        return InspectionResult(
            inspection_id=inspection_id,
            component_id=component_id,
            component_type=component_type,
            image_id=image_id or str(image_input),
            model_name=model_meta.get("model_type", vision_settings.VISION_MODEL_NAME),
            model_version=model_meta.get("version", vision_settings.VISION_MODEL_VERSION),
            detections=detections,
            processing_metadata=ProcessingMetadata(
                execution_time_ms=round(execution_latency, 2),
                preprocessing_time_ms=round(prep_latency, 2),
                inference_time_ms=round(inf_latency, 2),
                postprocessing_time_ms=round(post_latency, 2),
                device=self.model.device,
            )
        )

    def run_inspection_evidence(
        self,
        image_path: str,
        component_id: str,
        inspection_id: Optional[str] = None,
        component_type: str = "pipeline",
        confidence_threshold: Optional[float] = None,
        mask_artifact_path: Optional[str] = None
    ) -> VisionEvidence:
        """
        Executes full inspection pipeline and produces a versioned VisionEvidence contract.
        """
        t_total_start = time.perf_counter()

        # Step 1: Validation
        t_val_start = time.perf_counter()
        self.preprocessor.validate(image_path)
        val_latency = (time.perf_counter() - t_val_start) * 1000.0

        # Step 2: Preprocess
        t_prep_start = time.perf_counter()
        preprocessed_data = self.preprocessor.preprocess(image_path)
        prep_latency = (time.perf_counter() - t_prep_start) * 1000.0

        # Step 3: Model Inference Check
        if self.model is None or not self.model.is_loaded:
            raise ModelNotConfiguredError(
                "Inference cannot proceed: No vision model backend is configured or loaded in memory."
            )

        # Step 4: Forward inference
        t_inf_start = time.perf_counter()
        try:
            raw_predictions = self.model.predict(
                image_path,
                confidence_threshold=confidence_threshold
            )
        except TypeError:
            raw_predictions = self.model.predict(preprocessed_data)
        inf_latency = (time.perf_counter() - t_inf_start) * 1000.0

        # Step 5: Postprocessing
        t_post_start = time.perf_counter()
        model_meta = self.model.metadata()
        if isinstance(raw_predictions, list) and all(isinstance(d, Detection) for d in raw_predictions):
            detections = raw_predictions
        else:
            detections = self._post_process(raw_predictions)
        post_latency = (time.perf_counter() - t_post_start) * 1000.0

        # Step 6: Evidence Construction
        t_ev_start = time.perf_counter()
        total_so_far = (time.perf_counter() - t_total_start) * 1000.0
        trace = ProcessingTrace(
            validation_ms=round(val_latency, 2),
            preprocessing_ms=round(prep_latency, 2),
            inference_ms=round(inf_latency, 2),
            postprocessing_ms=round(post_latency, 2),
            evidence_construction_ms=0.0,
            total_execution_ms=round(total_so_far, 2)
        )

        evidence = EvidenceBuilder.build_evidence(
            image_path=image_path,
            model_meta=model_meta,
            detections=detections,
            trace=trace,
            component_id=component_id,
            inspection_id=inspection_id,
            component_type=component_type,
            mask_artifact_path=mask_artifact_path
        )
        ev_latency = (time.perf_counter() - t_ev_start) * 1000.0
        evidence.processing.evidence_construction_ms = round(ev_latency, 2)
        evidence.processing.total_execution_ms = round((time.perf_counter() - t_total_start) * 1000.0, 2)

        return evidence

    def _post_process(self, raw_predictions: Any) -> list:
        if hasattr(self.model, "post_process"):
            return self.model.post_process(raw_predictions)
        return []
