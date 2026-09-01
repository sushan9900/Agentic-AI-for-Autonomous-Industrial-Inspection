"""Unit tests for Phase 2A Decision Engine, Evidence Adapter, and Engineering Rules."""

import pytest
from backend.app.agents.decision_engine import DeterministicDecisionEngine
from backend.app.schemas.decision import (
    DecisionConfidence,
    InspectionDecision,
    InspectionPriority,
)
from backend.app.services.decision.evidence_adapter import EvidenceAdapter, EvidenceValueState
from backend.app.services.decision.rule_engine import InspectionRuleEngine
from vision.schemas.evidence import (
    DetectionEvidence,
    DetectionSummary,
    InspectionStatus,
    ModelProvenance,
    NormalizedBoundingBox,
    ProcessingTrace,
    QualityAssessment,
    QualityWarningType,
    SourceImageProvenance,
    VisionEvidence,
)
from vision.schemas.inspection import SeverityFeatures


def create_dummy_evidence(
    detections=None,
    quality_warnings=None,
    schema_version="1.0"
) -> VisionEvidence:
    """Helper to construct valid synthetic VisionEvidence fixtures."""
    trace = ProcessingTrace(
        validation_ms=0.5, preprocessing_ms=1.0, inference_ms=50.0,
        postprocessing_ms=0.5, evidence_construction_ms=0.2, total_execution_ms=52.2
    )
    img_prov = SourceImageProvenance(
        filename="test_sample.jpg", file_extension=".jpg", width=640, height=480,
        channels=3, file_size_bytes=45000, sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    mod_prov = ModelProvenance(
        model_name="YOLO11n-seg", model_architecture="YOLO11n-seg", model_version="1.0.0",
        checkpoint_identifier="best.pt", checkpoint_sha256="abc123def456", framework="ultralytics",
        framework_version="8.4.136", confidence_threshold=0.25, input_size=[640, 640], device="cpu"
    )
    
    warnings = quality_warnings or []
    quality = QualityAssessment(
        brightness_mean=120.0, contrast_std=45.0, blur_score=150.0,
        blur_detected=QualityWarningType.BLUR in warnings,
        low_contrast_detected=QualityWarningType.LOW_CONTRAST in warnings,
        underexposed=QualityWarningType.UNDEREXPOSURE in warnings,
        overexposed=QualityWarningType.OVEREXPOSURE in warnings,
        warnings=warnings
    )
    
    dets = detections or []
    status = InspectionStatus.QUALITY_WARNING if warnings else (
        InspectionStatus.NO_DETECTIONS if len(dets) == 0 else InspectionStatus.SUCCESS
    )

    confs = [d.confidence for d in dets]
    summary = DetectionSummary(
        detection_count=len(dets),
        max_confidence=max(confs) if confs else None,
        mean_confidence=(sum(confs) / len(confs)) if confs else None,
        min_confidence=min(confs) if confs else None
    )

    return VisionEvidence(
        schema_version=schema_version,
        inspection_id="insp-test-001",
        component_id="PIPE-4021",
        component_type="pipeline",
        status=status,
        source_image=img_prov,
        model=mod_prov,
        summary=summary,
        detections=dets,
        quality=quality,
        processing=trace
    )


def test_valid_evidence_produces_inspection_decision():
    bbox = NormalizedBoundingBox(
        x_pixel=10.0, y_pixel=10.0, width_pixel=50.0, height_pixel=30.0,
        x_norm=0.0156, y_norm=0.0208, width_norm=0.0781, height_norm=0.0625
    )
    det = DetectionEvidence(
        detection_id="det-001", class_id=0, defect_type="crack", confidence=0.85,
        bounding_box=bbox, segmentation=None,
        severity_features=SeverityFeatures(affected_area_percentage=2.0, crack_length_pixels=150.0, spread="localized")
    )
    evidence = create_dummy_evidence(detections=[det])
    
    engine = DeterministicDecisionEngine()
    decision = engine.evaluate(evidence)

    assert isinstance(decision, InspectionDecision)
    assert decision.schema_version == "1.0"
    assert decision.inspection_id == "insp-test-001"
    assert decision.priority in (InspectionPriority.LOW, InspectionPriority.MEDIUM, InspectionPriority.HIGH, InspectionPriority.CRITICAL)
    assert len(decision.rule_evaluations) == 7
    assert len(decision.decision_trace) == 4
    assert decision.evidence_references.source_image_filename == "test_sample.jpg"


def test_unsupported_schema_version_rejected():
    evidence = create_dummy_evidence(schema_version="2.0")
    engine = DeterministicDecisionEngine()
    with pytest.raises(ValueError) as exc:
        engine.evaluate(evidence)
    assert "Unsupported evidence schema version" in str(exc.value)


def test_no_detections_decision():
    evidence = create_dummy_evidence(detections=[])
    engine = DeterministicDecisionEngine()
    decision = engine.evaluate(evidence)

    assert decision.priority == InspectionPriority.LOW
    assert decision.confidence == DecisionConfidence.MEDIUM
    assert "No defect indications detected" in decision.defect_summary
    assert decision.requires_human_review is False


def test_quality_warning_triggers_review_required():
    evidence = create_dummy_evidence(quality_warnings=[QualityWarningType.BLUR])
    engine = DeterministicDecisionEngine()
    decision = engine.evaluate(evidence)

    assert decision.priority == InspectionPriority.REVIEW_REQUIRED
    assert decision.confidence == DecisionConfidence.LOW
    assert decision.requires_human_review is True
    # Verify RULE-QUAL-001 triggered
    qual_rule = next(r for r in decision.rule_evaluations if r.rule_id == "RULE-QUAL-001")
    assert qual_rule.triggered is True
    assert qual_rule.severity == InspectionPriority.REVIEW_REQUIRED


def test_high_affected_area_triggers_high_and_critical():
    bbox = NormalizedBoundingBox(
        x_pixel=0.0, y_pixel=0.0, width_pixel=200.0, height_pixel=200.0,
        x_norm=0.0, y_norm=0.0, width_norm=0.3125, height_norm=0.4167
    )
    
    # 1. High area (8.0% > 5.0%) -> Priority HIGH
    det_high = DetectionEvidence(
        detection_id="det-001", class_id=0, defect_type="crack", confidence=0.90,
        bounding_box=bbox,
        severity_features=SeverityFeatures(affected_area_percentage=8.0, crack_length_pixels=300.0)
    )
    decision_high = DeterministicDecisionEngine().evaluate(create_dummy_evidence(detections=[det_high]))
    assert decision_high.priority == InspectionPriority.HIGH
    assert decision_high.requires_human_review is True

    # 2. Critical area (15.0% > 12.0%) -> Priority CRITICAL
    det_crit = DetectionEvidence(
        detection_id="det-001", class_id=0, defect_type="crack", confidence=0.90,
        bounding_box=bbox,
        severity_features=SeverityFeatures(affected_area_percentage=15.0, crack_length_pixels=800.0)
    )
    decision_crit = DeterministicDecisionEngine().evaluate(create_dummy_evidence(detections=[det_crit]))
    assert decision_crit.priority == InspectionPriority.CRITICAL
    assert "IMMEDIATE ACTION REQUIRED" in decision_crit.recommended_action


def test_marginal_confidence_triggers_review_required():
    bbox = NormalizedBoundingBox(
        x_pixel=10.0, y_pixel=10.0, width_pixel=30.0, height_pixel=20.0,
        x_norm=0.0156, y_norm=0.0208, width_norm=0.0469, height_norm=0.0417
    )
    det_low_conf = DetectionEvidence(
        detection_id="det-001", class_id=0, defect_type="crack", confidence=0.28,  # < 0.35 threshold
        bounding_box=bbox,
        severity_features=SeverityFeatures(affected_area_percentage=1.0)
    )
    decision = DeterministicDecisionEngine().evaluate(create_dummy_evidence(detections=[det_low_conf]))
    assert decision.priority == InspectionPriority.REVIEW_REQUIRED
    assert decision.confidence == DecisionConfidence.LOW
    assert decision.requires_human_review is True


def test_multiple_defect_regions_rule_trigger():
    bbox = NormalizedBoundingBox(
        x_pixel=10.0, y_pixel=10.0, width_pixel=20.0, height_pixel=20.0,
        x_norm=0.01, y_norm=0.01, width_norm=0.03, height_norm=0.04
    )
    dets = [
        DetectionEvidence(
            detection_id=f"det-{i:03d}", class_id=0, defect_type="crack", confidence=0.75,
            bounding_box=bbox, severity_features=SeverityFeatures(affected_area_percentage=0.5)
        )
        for i in range(1, 5)  # 4 detections >= multiple_regions_threshold (3)
    ]
    decision = DeterministicDecisionEngine().evaluate(create_dummy_evidence(detections=dets))
    mult_rule = next(r for r in decision.rule_evaluations if r.rule_id == "RULE-SEV-004")
    assert mult_rule.triggered is True
    assert mult_rule.severity == InspectionPriority.MEDIUM


def test_decision_determinism_across_multiple_runs():
    bbox = NormalizedBoundingBox(
        x_pixel=10.0, y_pixel=10.0, width_pixel=50.0, height_pixel=30.0,
        x_norm=0.0156, y_norm=0.0208, width_norm=0.0781, height_norm=0.0625
    )
    det = DetectionEvidence(
        detection_id="det-001", class_id=0, defect_type="crack", confidence=0.85,
        bounding_box=bbox,
        severity_features=SeverityFeatures(affected_area_percentage=2.0, crack_length_pixels=150.0)
    )
    evidence = create_dummy_evidence(detections=[det])
    engine = DeterministicDecisionEngine()

    d1 = engine.evaluate(evidence)
    d2 = engine.evaluate(evidence)

    assert d1.priority == d2.priority
    assert d1.confidence == d2.confidence
    assert d1.recommended_action == d2.recommended_action
    assert len(d1.rule_evaluations) == len(d2.rule_evaluations)
    for r1, r2 in zip(d1.rule_evaluations, d2.rule_evaluations):
        assert r1.rule_id == r2.rule_id
        assert r1.triggered == r2.triggered
        assert r1.severity == r2.severity


def test_missing_fields_not_fabricated():
    # Empty detection list -> value states must be NOT_APPLICABLE
    evidence = create_dummy_evidence(detections=[])
    normalized = EvidenceAdapter.adapt(evidence)
    assert normalized.value_states["affected_area"] == EvidenceValueState.NOT_APPLICABLE
    assert normalized.value_states["crack_length"] == EvidenceValueState.NOT_APPLICABLE
    assert normalized.max_affected_area_pct is None
    assert normalized.max_crack_length_px is None
