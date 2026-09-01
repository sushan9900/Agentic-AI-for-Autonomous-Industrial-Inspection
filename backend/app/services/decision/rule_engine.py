"""Deterministic engineering rule evaluation engine (Phase 2A)."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from backend.app.schemas.decision import InspectionPriority, RuleEvaluation
from backend.app.services.decision.evidence_adapter import NormalizedInspectionEvidence
from vision.schemas.evidence import InspectionStatus

DEFAULT_CONFIG_PATH = Path("configs/decision_rules.yaml")


class BaseInspectionRule(ABC):
    """Abstract base class for deterministic inspection rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        pass

    @abstractmethod
    def evaluate(
        self,
        evidence: NormalizedInspectionEvidence,
        config: Dict[str, Any]
    ) -> RuleEvaluation:
        pass


class ImageQualityWarningRule(BaseInspectionRule):
    """Evaluates image quality degradation and warning flags."""

    @property
    def rule_id(self) -> str:
        return "RULE-QUAL-001"

    @property
    def rule_name(self) -> str:
        return "Image Quality Impairment Warning"

    def evaluate(
        self,
        evidence: NormalizedInspectionEvidence,
        config: Dict[str, Any]
    ) -> RuleEvaluation:
        triggered = len(evidence.quality_warnings) > 0 or evidence.status == InspectionStatus.QUALITY_WARNING
        warning_names = [w.value for w in evidence.quality_warnings]
        
        if triggered:
            explanation = (
                f"Image quality impairment detected: {', '.join(warning_names)}. "
                "Visual evidence reliability is degraded and requires human inspection verification."
            )
            severity = InspectionPriority.REVIEW_REQUIRED
        else:
            explanation = "Image quality metrics satisfy standard development clarity thresholds."
            severity = InspectionPriority.LOW

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            triggered=triggered,
            severity=severity,
            explanation=explanation,
            evidence_fields_used=["quality.warnings", "quality.blur_detected", "quality.low_contrast_detected"]
        )


class NoDetectionRule(BaseInspectionRule):
    """Evaluates clean visual evidence with zero defect detections."""

    @property
    def rule_id(self) -> str:
        return "RULE-DET-000"

    @property
    def rule_name(self) -> str:
        return "No Defect Indications Detected"

    def evaluate(
        self,
        evidence: NormalizedInspectionEvidence,
        config: Dict[str, Any]
    ) -> RuleEvaluation:
        triggered = evidence.detection_count == 0 and len(evidence.quality_warnings) == 0

        if triggered:
            explanation = (
                "No physical defect indications detected above active confidence threshold in the visual evidence. "
                "Note: Clean visual evidence does not guarantee structural integrity under non-visual failure modes."
            )
            severity = InspectionPriority.LOW
        else:
            explanation = f"Defect indications present in visual evidence ({evidence.detection_count} detections found)."
            severity = InspectionPriority.LOW

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            triggered=triggered,
            severity=severity,
            explanation=explanation,
            evidence_fields_used=["detection_count", "status"]
        )


class HighAffectedAreaRule(BaseInspectionRule):
    """Evaluates defect surface area coverage."""

    @property
    def rule_id(self) -> str:
        return "RULE-SEV-001"

    @property
    def rule_name(self) -> str:
        return "High Defect Surface Area Coverage"

    def evaluate(
        self,
        evidence: NormalizedInspectionEvidence,
        config: Dict[str, Any]
    ) -> RuleEvaluation:
        thresholds = config.get("thresholds", {})
        high_thresh = thresholds.get("high_affected_area_pct", 5.0)
        crit_thresh = thresholds.get("critical_affected_area_pct", 12.0)

        max_area = evidence.max_affected_area_pct or 0.0
        triggered = max_area >= high_thresh

        if max_area >= crit_thresh:
            severity = InspectionPriority.CRITICAL
            explanation = (
                f"Critical surface defect area coverage ({max_area:.2f}% >= {crit_thresh}%). "
                "Significant material disruption detected requiring immediate structural integrity assessment."
            )
        elif max_area >= high_thresh:
            severity = InspectionPriority.HIGH
            explanation = (
                f"High surface defect area coverage ({max_area:.2f}% >= {high_thresh}%). "
                "Elevated material surface compromise detected requiring expedited maintenance review."
            )
        else:
            severity = InspectionPriority.LOW
            explanation = f"Surface defect area ({max_area:.2f}%) within development baseline thresholds (< {high_thresh}%)."

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            triggered=triggered,
            severity=severity,
            explanation=explanation,
            evidence_fields_used=["max_affected_area_pct", "total_affected_area_pct"]
        )


class LargeBoundingRegionRule(BaseInspectionRule):
    """Evaluates bounding region spatial span."""

    @property
    def rule_id(self) -> str:
        return "RULE-SEV-002"

    @property
    def rule_name(self) -> str:
        return "Large Defect Spatial Bounding Region"

    def evaluate(
        self,
        evidence: NormalizedInspectionEvidence,
        config: Dict[str, Any]
    ) -> RuleEvaluation:
        thresholds = config.get("thresholds", {})
        large_thresh = thresholds.get("large_bounding_region_pct", 15.0)
        crit_thresh = thresholds.get("critical_bounding_region_pct", 35.0)

        max_box = evidence.max_bounding_box_pct or 0.0
        triggered = max_box >= large_thresh

        if max_box >= crit_thresh:
            severity = InspectionPriority.CRITICAL
            explanation = f"Critical spatial bounding span ({max_box:.2f}% >= {crit_thresh}% of frame)."
        elif max_box >= large_thresh:
            severity = InspectionPriority.HIGH
            explanation = f"Extensive spatial bounding span ({max_box:.2f}% >= {large_thresh}% of frame)."
        else:
            severity = InspectionPriority.LOW
            explanation = f"Bounding region spatial span ({max_box:.2f}%) within standard baseline."

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            triggered=triggered,
            severity=severity,
            explanation=explanation,
            evidence_fields_used=["max_bounding_box_pct"]
        )


class ExtensiveCrackLengthRule(BaseInspectionRule):
    """Evaluates estimated continuous crack propagation length."""

    @property
    def rule_id(self) -> str:
        return "RULE-SEV-003"

    @property
    def rule_name(self) -> str:
        return "Extensive Crack Propagation Length"

    def evaluate(
        self,
        evidence: NormalizedInspectionEvidence,
        config: Dict[str, Any]
    ) -> RuleEvaluation:
        thresholds = config.get("thresholds", {})
        ext_thresh = thresholds.get("extensive_crack_length_px", 450.0)
        crit_thresh = thresholds.get("critical_crack_length_px", 750.0)

        max_len = evidence.max_crack_length_px or 0.0
        triggered = max_len >= ext_thresh

        if max_len >= crit_thresh:
            severity = InspectionPriority.CRITICAL
            explanation = (
                f"Critical crack propagation length estimated at {max_len:.1f}px (>= {crit_thresh}px). "
                "Severe structural fracture propagation indicated."
            )
        elif max_len >= ext_thresh:
            severity = InspectionPriority.HIGH
            explanation = (
                f"Extensive crack propagation length estimated at {max_len:.1f}px (>= {ext_thresh}px). "
                "Elevated fracture propagation observed."
            )
        else:
            severity = InspectionPriority.LOW
            explanation = f"Estimated crack length ({max_len:.1f}px) below extensive threshold ({ext_thresh}px)."

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            triggered=triggered,
            severity=severity,
            explanation=explanation,
            evidence_fields_used=["max_crack_length_px"]
        )


class MultipleDefectRegionsRule(BaseInspectionRule):
    """Evaluates multi-region defect density in a single image."""

    @property
    def rule_id(self) -> str:
        return "RULE-SEV-004"

    @property
    def rule_name(self) -> str:
        return "Multiple Defect Regions Detected"

    def evaluate(
        self,
        evidence: NormalizedInspectionEvidence,
        config: Dict[str, Any]
    ) -> RuleEvaluation:
        thresholds = config.get("thresholds", {})
        mult_thresh = thresholds.get("multiple_regions_threshold", 3)
        dense_thresh = thresholds.get("dense_cluster_threshold", 6)

        count = evidence.detection_count
        triggered = count >= mult_thresh

        if count >= dense_thresh:
            severity = InspectionPriority.HIGH
            explanation = (
                f"Dense defect clustering: {count} distinct defect regions detected in a single component frame (>= {dense_thresh})."
            )
        elif count >= mult_thresh:
            severity = InspectionPriority.MEDIUM
            explanation = (
                f"Multiple defect regions: {count} distinct indications detected in a single component frame (>= {mult_thresh})."
            )
        else:
            severity = InspectionPriority.LOW
            explanation = f"Defect region count ({count}) below multi-region cluster threshold ({mult_thresh})."

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            triggered=triggered,
            severity=severity,
            explanation=explanation,
            evidence_fields_used=["detection_count", "detection_ids"]
        )


class LowModelConfidenceRule(BaseInspectionRule):
    """Evaluates marginal detection confidence requiring verification."""

    @property
    def rule_id(self) -> str:
        return "RULE-CONF-001"

    @property
    def rule_name(self) -> str:
        return "Marginal Model Confidence Verification"

    def evaluate(
        self,
        evidence: NormalizedInspectionEvidence,
        config: Dict[str, Any]
    ) -> RuleEvaluation:
        thresholds = config.get("thresholds", {})
        low_conf_thresh = thresholds.get("low_confidence", 0.35)

        min_c = evidence.min_confidence
        triggered = bool(evidence.detection_count > 0 and min_c is not None and min_c < low_conf_thresh)

        if triggered:
            explanation = (
                f"One or more defect detections exhibit marginal model confidence ({min_c:.2f} < {low_conf_thresh}). "
                "Human inspector review is required to confirm physical presence and prevent false alarms."
            )
            severity = InspectionPriority.REVIEW_REQUIRED
        else:
            explanation = f"Detection confidence scores satisfy standard development thresholds (>= {low_conf_thresh})."
            severity = InspectionPriority.LOW

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            triggered=triggered,
            severity=severity,
            explanation=explanation,
            evidence_fields_used=["min_confidence", "mean_confidence"]
        )


class InspectionRuleEngine:
    """Orchestrates deterministic rule evaluation against normalized inspection evidence."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.rules: List[BaseInspectionRule] = [
            ImageQualityWarningRule(),
            NoDetectionRule(),
            HighAffectedAreaRule(),
            LargeBoundingRegionRule(),
            ExtensiveCrackLengthRule(),
            MultipleDefectRegionsRule(),
            LowModelConfidenceRule(),
        ]

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {"development_only": True, "thresholds": {}}

    def evaluate(self, evidence: NormalizedInspectionEvidence) -> List[RuleEvaluation]:
        """Evaluates all registered rules in deterministic order."""
        evaluations: List[RuleEvaluation] = []
        for rule in self.rules:
            eval_res = rule.evaluate(evidence, self.config)
            evaluations.append(eval_res)
        return evaluations
