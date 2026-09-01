"""End-to-end Autonomous Industrial Inspection Service (Phase 3C).

Orchestrates the complete inspection pipeline:
Raw Image -> Preprocessing -> YOLO11n-seg Model -> VisionEvidence v1.0 ->
InspectionDecisionAgent (11 stages) -> PostgreSQL Persistence -> Structured Response.
"""

from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from backend.app.agents.inspection_agent import inspection_decision_agent
from backend.app.database.session import SessionLocal
from backend.app.schemas.agent_decision import AgentInspectionDecision
from backend.app.services.agent import agent_decision_service
from vision.config.settings import vision_settings
from vision.inference.pipeline import InferencePipeline
from vision.models.yolo_seg import YOLOSegmentationModel
from vision.schemas.evidence import VisionEvidence


class EndToEndInspectionService:
    """Orchestrates end-to-end vision perception, multi-modal agent reasoning, and audit persistence."""

    def __init__(self, model_checkpoint_path: Optional[str] = None, device: Optional[str] = None):
        self.checkpoint_path = model_checkpoint_path or "experiments/vision/deepcrack/baseline/weights/best.pt"
        self.device = device or ("cuda" if vision_settings.VISION_DEVICE == "cuda" else "cpu")
        self._pipeline: Optional[InferencePipeline] = None

    def _get_pipeline(self) -> InferencePipeline:
        """Lazily initializes and loads the YOLO inference pipeline."""
        if self._pipeline is None:
            model = YOLOSegmentationModel(
                model_path=self.checkpoint_path,
                device=self.device,
                confidence_threshold=vision_settings.VISION_CONFIDENCE_THRESHOLD
            )
            model.load()
            self._pipeline = InferencePipeline(model=model)
        return self._pipeline

    def run_e2e_inspection(
        self,
        image_path: str,
        asset_id: str,
        component_id: Optional[str] = None,
        inspection_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        db: Optional[Session] = None
    ) -> AgentInspectionDecision:
        """Executes the complete autonomous inspection flow."""
        t_start = time.perf_counter()

        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Inspection source image not found at: {image_path}")

        session_created = False
        if db is None:
            db = SessionLocal()
            session_created = True

        try:
            # 1. Vision Perception Execution
            pipeline = self._get_pipeline()
            assigned_insp_id = inspection_id or f"insp-{image_path_obj.stem}-{int(time.time())}"
            target_comp_id = component_id or "PIPE-SEG-4021"

            vision_evidence: VisionEvidence = pipeline.run_inspection_evidence(
                image_path=str(image_path_obj),
                component_id=target_comp_id,
                inspection_id=assigned_insp_id,
                component_type="pipeline",
                confidence_threshold=confidence_threshold
            )

            # 2. Agent Reasoning Execution (11 stages)
            decision = inspection_decision_agent.run_inspection(
                inspection_id=vision_evidence.inspection_id,
                asset_id=asset_id,
                evidence=vision_evidence,
                db=db,
                component_id=target_comp_id
            )

            # 3. PostgreSQL Persistence
            t_persist_start = time.perf_counter()
            agent_decision_service.save_decision(db=db, decision=decision)
            persist_latency_ms = (time.perf_counter() - t_persist_start) * 1000.0

            total_latency_ms = (time.perf_counter() - t_start) * 1000.0

            # Attach performance latencies
            latencies = {
                "vision_validation_ms": vision_evidence.processing.validation_ms,
                "vision_preprocessing_ms": vision_evidence.processing.preprocessing_ms,
                "yolo_inference_ms": vision_evidence.processing.inference_ms,
                "vision_postprocessing_ms": vision_evidence.processing.postprocessing_ms,
                "evidence_construction_ms": vision_evidence.processing.evidence_construction_ms,
                "total_vision_execution_ms": vision_evidence.processing.total_execution_ms,
                "agent_total_ms": decision.execution_metrics.get("total_duration_ms", 0.0),
                "persistence_ms": round(persist_latency_ms, 2),
                "end_to_end_total_ms": round(total_latency_ms, 2)
            }
            decision.execution_metrics["latencies_breakdown"] = latencies

            return decision

        finally:
            if session_created:
                db.close()


# Global singleton service
e2e_inspection_service = EndToEndInspectionService()
