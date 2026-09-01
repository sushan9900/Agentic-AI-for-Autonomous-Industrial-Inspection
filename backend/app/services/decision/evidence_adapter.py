"""Evidence adapter: transforms VisionEvidence v1.0 into normalized decision inputs."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.decision import EvidenceValueState
from vision.schemas.evidence import InspectionStatus, QualityWarningType, VisionEvidence


class NormalizedInspectionEvidence(BaseModel):
    """Internal normalized representation of inspection evidence for deterministic rule evaluation."""
    inspection_id: str
    component_id: str
    component_type: str
    status: InspectionStatus
    
    # Provenance
    source_image_filename: str
    source_image_sha256: str
    model_checkpoint_sha256: str
    model_name: str
    
    # Quality Flags
    quality_warnings: List[QualityWarningType]
    blur_detected: bool
    low_contrast_detected: bool
    underexposed: bool
    overexposed: bool
    
    # Detection Aggregations
    detection_count: int
    detection_ids: List[str]
    defect_types: List[str]
    max_confidence: Optional[float] = None
    mean_confidence: Optional[float] = None
    min_confidence: Optional[float] = None
    
    # Measurable Severity Metrics
    max_affected_area_pct: Optional[float] = None
    total_affected_area_pct: Optional[float] = None
    max_bounding_box_pct: Optional[float] = None
    max_crack_length_px: Optional[float] = None
    max_crack_width_px: Optional[float] = None
    
    # Value State Tracking (KNOWN / UNKNOWN / NOT_APPLICABLE)
    value_states: Dict[str, EvidenceValueState] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class EvidenceAdapter:
    """Adapts and normalizes VisionEvidence v1.0 contracts."""

    @staticmethod
    def adapt(evidence: VisionEvidence) -> NormalizedInspectionEvidence:
        """
        Normalizes a VisionEvidence contract without inventing missing fields.
        """
        # Validate schema version
        if evidence.schema_version != "1.0":
            raise ValueError(f"Unsupported evidence schema version '{evidence.schema_version}'. Expected '1.0'.")

        value_states: Dict[str, EvidenceValueState] = {}
        
        det_count = len(evidence.detections)
        det_ids = [d.detection_id for d in evidence.detections]
        defect_types = sorted(list(set(d.defect_type for d in evidence.detections)))

        # Confidences
        confidences = [d.confidence for d in evidence.detections]
        max_conf = max(confidences) if confidences else None
        min_conf = min(confidences) if confidences else None
        mean_conf = (sum(confidences) / len(confidences)) if confidences else None

        value_states["confidence"] = EvidenceValueState.KNOWN if confidences else EvidenceValueState.NOT_APPLICABLE

        # Measurable severity features using safe getattr
        affected_areas = []
        for d in evidence.detections:
            if d.severity_features:
                val = getattr(d.severity_features, "affected_area_percentage", None)
                if val is not None:
                    affected_areas.append(val)
            elif d.segmentation and d.segmentation.mask_area_percentage is not None:
                affected_areas.append(d.segmentation.mask_area_percentage)

        max_aff_pct = max(affected_areas) if affected_areas else None
        tot_aff_pct = sum(affected_areas) if affected_areas else None
        value_states["affected_area"] = EvidenceValueState.KNOWN if affected_areas else (
            EvidenceValueState.NOT_APPLICABLE if det_count == 0 else EvidenceValueState.UNKNOWN
        )

        bbox_areas = []
        for d in evidence.detections:
            # Check bounding box normalized area or severity feature
            if d.bounding_box:
                w_norm = getattr(d.bounding_box, "width_norm", None)
                h_norm = getattr(d.bounding_box, "height_norm", None)
                if w_norm is not None and h_norm is not None:
                    bbox_areas.append(round(w_norm * h_norm * 100.0, 4))
            elif d.severity_features:
                val = getattr(d.severity_features, "bounding_box_area_percentage", None)
                if val is not None:
                    bbox_areas.append(val)

        max_bbox_pct = max(bbox_areas) if bbox_areas else None
        value_states["bounding_box_area"] = EvidenceValueState.KNOWN if bbox_areas else (
            EvidenceValueState.NOT_APPLICABLE if det_count == 0 else EvidenceValueState.UNKNOWN
        )

        crack_lengths = []
        for d in evidence.detections:
            if d.severity_features:
                val = getattr(d.severity_features, "crack_length_pixels", None)
                if val is not None:
                    crack_lengths.append(val)
            elif d.bounding_box:
                # Estimate from pixel box diagonal
                w_px = getattr(d.bounding_box, "width_pixel", 0.0)
                h_px = getattr(d.bounding_box, "height_pixel", 0.0)
                if w_px > 0 or h_px > 0:
                    crack_lengths.append(round((w_px**2 + h_px**2) ** 0.5, 2))

        max_crack_len = max(crack_lengths) if crack_lengths else None
        value_states["crack_length"] = EvidenceValueState.KNOWN if crack_lengths else (
            EvidenceValueState.NOT_APPLICABLE if det_count == 0 else EvidenceValueState.UNKNOWN
        )

        crack_widths = []
        for d in evidence.detections:
            if d.severity_features:
                val = getattr(d.severity_features, "crack_width_estimate_pixels", None)
                if val is not None:
                    crack_widths.append(val)

        max_crack_w = max(crack_widths) if crack_widths else None
        value_states["crack_width"] = EvidenceValueState.KNOWN if crack_widths else (
            EvidenceValueState.NOT_APPLICABLE if det_count == 0 else EvidenceValueState.UNKNOWN
        )

        return NormalizedInspectionEvidence(
            inspection_id=evidence.inspection_id,
            component_id=evidence.component_id,
            component_type=evidence.component_type,
            status=evidence.status,
            source_image_filename=evidence.source_image.filename,
            source_image_sha256=evidence.source_image.sha256_hash,
            model_checkpoint_sha256=evidence.model.checkpoint_sha256,
            model_name=evidence.model.model_name,
            quality_warnings=evidence.quality.warnings,
            blur_detected=evidence.quality.blur_detected,
            low_contrast_detected=evidence.quality.low_contrast_detected,
            underexposed=evidence.quality.underexposed,
            overexposed=evidence.quality.overexposed,
            detection_count=det_count,
            detection_ids=det_ids,
            defect_types=defect_types,
            max_confidence=max_conf,
            mean_confidence=mean_conf,
            min_confidence=min_conf,
            max_affected_area_pct=max_aff_pct,
            total_affected_area_pct=tot_aff_pct,
            max_bounding_box_pct=max_bbox_pct,
            max_crack_length_px=max_crack_len,
            max_crack_width_px=max_crack_w,
            value_states=value_states
        )
