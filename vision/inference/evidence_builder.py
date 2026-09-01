"""Vision evidence builder assembling versioned VisionEvidence contracts."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import cv2
import numpy as np
from vision.inference.quality import assess_image_quality
from vision.inference.severity import extract_severity_features
from vision.schemas.evidence import (
    DetectionEvidence,
    DetectionSummary,
    InspectionStatus,
    ModelProvenance,
    NormalizedBoundingBox,
    ProcessingTrace,
    QualityAssessment,
    SegmentationEvidence,
    SourceImageProvenance,
    VisionEvidence,
)
from vision.schemas.inspection import Detection, SeverityFeatures


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """Computes SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(512 * 1024):
            h.update(chunk)
    return h.hexdigest()


class EvidenceBuilder:
    """Builder class to construct reproducible, auditable VisionEvidence instances."""

    @staticmethod
    def build_evidence(
        image_path: Union[str, Path],
        model_meta: Dict[str, Any],
        detections: List[Detection],
        trace: ProcessingTrace,
        component_id: str,
        inspection_id: Optional[str] = None,
        component_type: str = "pipeline",
        mask_artifact_path: Optional[str] = None,
    ) -> VisionEvidence:
        """Assembles a validated VisionEvidence contract."""
        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Source image not found: {img_path}")

        # 1. Source Image Provenance
        img = cv2.imread(str(img_path))
        if img is None:
            raise ValueError(f"Failed to read image content from {img_path}")
        h, w = img.shape[:2]
        channels = img.shape[2] if len(img.shape) == 3 else 1
        file_size = img_path.stat().st_size
        img_sha256 = compute_file_sha256(img_path)

        source_provenance = SourceImageProvenance(
            filename=img_path.name,
            file_extension=img_path.suffix.lower(),
            width=w,
            height=h,
            channels=channels,
            file_size_bytes=file_size,
            sha256_hash=img_sha256
        )

        # 2. Model Provenance
        ckpt_path = Path(model_meta.get("model_path", ""))
        ckpt_sha256 = compute_file_sha256(ckpt_path) if ckpt_path.exists() else "unspecified"

        model_provenance = ModelProvenance(
            model_name=model_meta.get("model_type", "YOLO11n-seg"),
            model_architecture=model_meta.get("model_type", "YOLO11n-seg"),
            model_version=model_meta.get("version", "1.0.0"),
            checkpoint_identifier=ckpt_path.name if ckpt_path.name else "best.pt",
            checkpoint_sha256=ckpt_sha256,
            framework="ultralytics",
            framework_version=model_meta.get("framework_version", "8.4.136"),
            confidence_threshold=float(model_meta.get("confidence_threshold", 0.25)),
            input_size=[640, 640],
            device=str(model_meta.get("device", "cpu"))
        )

        # 3. Quality Assessment
        quality = assess_image_quality(img)

        # 4. Deterministic Detections Ordering & Formatting
        # Sort by confidence descending, then by x, y for perfect determinism
        sorted_detections = sorted(
            detections,
            key=lambda d: (-d.confidence, d.bounding_box.x, d.bounding_box.y)
        )

        det_evidence_list: List[DetectionEvidence] = []
        confidences: List[float] = []

        for idx, d in enumerate(sorted_detections, start=1):
            det_id = f"det-{idx:03d}"
            confidences.append(d.confidence)

            # Dual bounding box
            x_norm = min(max(d.bounding_box.x / w, 0.0), 1.0)
            y_norm = min(max(d.bounding_box.y / h, 0.0), 1.0)
            w_norm = min(max(d.bounding_box.width / w, 0.0), 1.0)
            h_norm = min(max(d.bounding_box.height / h, 0.0), 1.0)

            bbox_norm = NormalizedBoundingBox(
                x_pixel=round(d.bounding_box.x, 2),
                y_pixel=round(d.bounding_box.y, 2),
                width_pixel=round(d.bounding_box.width, 2),
                height_pixel=round(d.bounding_box.height, 2),
                x_norm=round(x_norm, 4),
                y_norm=round(y_norm, 4),
                width_norm=round(w_norm, 4),
                height_norm=round(h_norm, 4)
            )

            # Segmentation evidence
            seg_ev = None
            if d.severity_features and d.severity_features.affected_area_percentage is not None:
                area_pct = d.severity_features.affected_area_percentage
                area_px = (area_pct / 100.0) * (w * h)
                seg_ev = SegmentationEvidence(
                    polygon_count=1,
                    normalized_polygons=[],
                    mask_area_pixels=round(area_px, 2),
                    mask_area_percentage=round(area_pct, 4),
                    mask_artifact_path=mask_artifact_path
                )

            sev_feat = d.severity_features or extract_severity_features(d.bounding_box, w, h)

            det_ev = DetectionEvidence(
                detection_id=det_id,
                class_id=0,
                defect_type=d.defect_type,
                confidence=round(d.confidence, 4),
                bounding_box=bbox_norm,
                segmentation=seg_ev,
                severity_features=sev_feat
            )
            det_evidence_list.append(det_ev)

        # 5. Detection Summary
        summary = DetectionSummary(
            detection_count=len(det_evidence_list),
            max_confidence=round(max(confidences), 4) if confidences else None,
            mean_confidence=round(sum(confidences) / len(confidences), 4) if confidences else None,
            min_confidence=round(min(confidences), 4) if confidences else None
        )

        # 6. Operational Status Determination
        if len(quality.warnings) > 0:
            status = InspectionStatus.QUALITY_WARNING
        elif len(det_evidence_list) == 0:
            status = InspectionStatus.NO_DETECTIONS
        else:
            status = InspectionStatus.SUCCESS

        # Deterministic inspection ID if not provided: insp-<image_stem>-<hash_prefix>
        final_insp_id = inspection_id or f"insp-{img_path.stem}-{img_sha256[:8]}"

        return VisionEvidence(
            schema_version="1.0",
            inspection_id=final_insp_id,
            component_id=component_id,
            component_type=component_type,
            status=status,
            source_image=source_provenance,
            model=model_provenance,
            summary=summary,
            detections=det_evidence_list,
            quality=quality,
            processing=trace
        )

    @staticmethod
    def save_evidence(evidence: VisionEvidence, output_path: Union[str, Path]) -> None:
        """Serializes VisionEvidence contract to clean JSON file."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(evidence.model_dump_json(indent=2))
