"""Inspection Learning and Error Pattern Detection Service (Phase 7C/7D)."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.database.models.inspection_outcome import InspectionOutcomeModel
from backend.app.schemas.learning_metrics import (
    DetectedPattern,
    LearningMetricsSummary,
    LearningPatternsResponse,
    PredictionOutcomeComparison,
)


class InspectionLearningService:
    """
    Deterministic evaluation service that compares AI predictions with verified human review outcomes.
    Calculates agreement metrics and identifies recurring error patterns. Pure deterministic execution.
    """

    SEVERITY_RANKS: Dict[str, int] = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "MODERATE": 2,
        "LOW": 1,
        "NONE": 0,
        "UNKNOWN": 0,
    }

    @staticmethod
    def get_risk_band(score: int) -> str:
        """Standardized risk band categorization."""
        if score >= 80:
            return "CRITICAL"
        if score >= 60:
            return "HIGH"
        if score >= 40:
            return "MEDIUM"
        return "LOW"

    def compare_single(self, record: InspectionOutcomeModel) -> PredictionOutcomeComparison:
        """Evaluates a single recorded outcome against its AI prediction snapshot."""
        ai_data = record.ai_prediction_snapshot or {}
        conf_data = record.confirmed_outcome_snapshot or {}

        ai_defect = bool(ai_data.get("ai_defect_detected", False))
        conf_defect = bool(conf_data.get("confirmed_defect_present", False))
        defect_agreed = (ai_defect == conf_defect)

        ai_sev = (ai_data.get("ai_severity") or "LOW").strip().upper()
        conf_sev = (conf_data.get("confirmed_severity") or "LOW").strip().upper()
        severity_agreed = (ai_sev == conf_sev)

        ai_risk_score = int(ai_data.get("ai_risk_score", 0))
        ai_band = self.get_risk_band(ai_risk_score)

        # Determine confirmed risk band from confirmed severity
        if conf_sev == "CRITICAL":
            conf_band = "CRITICAL"
        elif conf_sev == "HIGH":
            conf_band = "HIGH"
        elif conf_sev in ("MEDIUM", "MODERATE"):
            conf_band = "MEDIUM"
        else:
            conf_band = "LOW"
        risk_band_agreed = (ai_band == conf_band)

        # Action agreement: did the reviewer approve the operational action without modification?
        corr = conf_data.get("reviewer_correction") or {}
        action_modified = bool(corr.get("corrected_action")) or (record.review_status == "REJECTED")
        action_agreed = not action_modified

        # False positive / negative determination
        is_fp = (ai_defect is True and conf_defect is False)
        is_fn = (ai_defect is False and conf_defect is True)

        # Severity delta (+ overestimation, - underestimation)
        ai_rank = self.SEVERITY_RANKS.get(ai_sev, 1)
        conf_rank = self.SEVERITY_RANKS.get(conf_sev, 1)
        sev_delta = ai_rank - conf_rank

        return PredictionOutcomeComparison(
            inspection_id=record.inspection_id,
            asset_id=record.asset_id,
            component_id=record.component_id,
            defect_agreement=defect_agreed,
            severity_agreement=severity_agreed,
            risk_band_agreement=risk_band_agreed,
            action_agreement=action_agreed,
            is_false_positive=is_fp,
            is_false_negative=is_fn,
            severity_delta=sev_delta,
            ai_severity=ai_sev,
            confirmed_severity=conf_sev,
            ai_risk_score=ai_risk_score,
            review_status=record.review_status
        )

    def calculate_metrics(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None
    ) -> LearningMetricsSummary:
        """Computes aggregate learning metrics across historical review outcomes."""
        query = db.query(InspectionOutcomeModel)
        if asset_id:
            query = query.filter(InspectionOutcomeModel.asset_id == asset_id)
        if component_id:
            query = query.filter(InspectionOutcomeModel.component_id == component_id)

        records: List[InspectionOutcomeModel] = query.all()
        total = len(records)

        if total == 0:
            return LearningMetricsSummary(
                total_reviewed=0,
                defect_agreement_rate=0.0,
                severity_agreement_rate=0.0,
                risk_band_agreement_rate=0.0,
                action_agreement_rate=0.0,
                overall_reviewer_agreement_rate=0.0,
                false_positive_count=0,
                false_positive_rate=0.0,
                false_negative_count=0,
                false_negative_rate=0.0,
                correction_count=0,
                correction_rate=0.0,
                severity_overestimation_count=0,
                severity_underestimation_count=0,
                methodology_version="1.0"
            )

        defect_agreed_cnt = 0
        sev_agreed_cnt = 0
        risk_agreed_cnt = 0
        action_agreed_cnt = 0
        full_agreed_cnt = 0

        fp_cnt = 0
        fn_cnt = 0
        corr_cnt = 0
        sev_over_cnt = 0
        sev_under_cnt = 0

        for r in records:
            comp = self.compare_single(r)
            if comp.defect_agreement:
                defect_agreed_cnt += 1
            if comp.severity_agreement:
                sev_agreed_cnt += 1
            if comp.risk_band_agreement:
                risk_agreed_cnt += 1
            if comp.action_agreement:
                action_agreed_cnt += 1
            if r.review_status == "APPROVED" and comp.defect_agreement and comp.severity_agreement:
                full_agreed_cnt += 1

            if comp.is_false_positive:
                fp_cnt += 1
            if comp.is_false_negative:
                fn_cnt += 1
            if r.review_status in ("CORRECTED", "REJECTED"):
                corr_cnt += 1

            if comp.severity_delta > 0:
                sev_over_cnt += 1
            elif comp.severity_delta < 0:
                sev_under_cnt += 1

        return LearningMetricsSummary(
            total_reviewed=total,
            defect_agreement_rate=round(defect_agreed_cnt / total, 4),
            severity_agreement_rate=round(sev_agreed_cnt / total, 4),
            risk_band_agreement_rate=round(risk_agreed_cnt / total, 4),
            action_agreement_rate=round(action_agreed_cnt / total, 4),
            overall_reviewer_agreement_rate=round(full_agreed_cnt / total, 4),
            false_positive_count=fp_cnt,
            false_positive_rate=round(fp_cnt / total, 4),
            false_negative_count=fn_cnt,
            false_negative_rate=round(fn_cnt / total, 4),
            correction_count=corr_cnt,
            correction_rate=round(corr_cnt / total, 4),
            severity_overestimation_count=sev_over_cnt,
            severity_underestimation_count=sev_under_cnt,
            methodology_version="1.0"
        )

    def detect_error_patterns(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None
    ) -> List[DetectedPattern]:
        """
        Detects recurring prediction discrepancies (>= 2 occurrences) grouped by asset and component.
        Deterministic detection; no LLM.
        """
        query = db.query(InspectionOutcomeModel)
        if asset_id:
            query = query.filter(InspectionOutcomeModel.asset_id == asset_id)
        if component_id:
            query = query.filter(InspectionOutcomeModel.component_id == component_id)

        records: List[InspectionOutcomeModel] = query.order_by(InspectionOutcomeModel.reviewed_at.asc()).all()
        if not records:
            return []

        # Group comparisons by (asset_id, component_id)
        fp_buckets: Dict[Tuple[str, Optional[str]], List[Tuple[str, datetime]]] = {}
        fn_buckets: Dict[Tuple[str, Optional[str]], List[Tuple[str, datetime]]] = {}
        over_buckets: Dict[Tuple[str, Optional[str]], List[Tuple[str, datetime]]] = {}
        under_buckets: Dict[Tuple[str, Optional[str]], List[Tuple[str, datetime]]] = {}
        action_buckets: Dict[Tuple[str, Optional[str]], List[Tuple[str, datetime]]] = {}

        for r in records:
            comp = self.compare_single(r)
            key = (r.asset_id, r.component_id)
            ts = r.reviewed_at or r.created_at

            if comp.is_false_positive:
                fp_buckets.setdefault(key, []).append((r.inspection_id, ts))
            if comp.is_false_negative:
                fn_buckets.setdefault(key, []).append((r.inspection_id, ts))
            if comp.severity_delta > 0:
                over_buckets.setdefault(key, []).append((r.inspection_id, ts))
            elif comp.severity_delta < 0:
                under_buckets.setdefault(key, []).append((r.inspection_id, ts))
            if not comp.action_agreement:
                action_buckets.setdefault(key, []).append((r.inspection_id, ts))

        patterns: List[DetectedPattern] = []

        def _add_patterns(
            buckets: Dict[Tuple[str, Optional[str]], List[Tuple[str, datetime]]],
            pattern_type: str,
            desc_template: str
        ):
            for (a_id, c_id), items in buckets.items():
                if len(items) >= 2:
                    p_id = f"pat-{pattern_type.lower()}-{a_id}-{c_id or 'all'}"
                    insp_ids = [item[0] for item in items]
                    timestamps = [item[1] for item in items]
                    comp_str = f" on component '{c_id}'" if c_id else ""
                    explanation = desc_template.format(count=len(items), asset=a_id, comp=comp_str)

                    patterns.append(
                        DetectedPattern(
                            pattern_id=p_id,
                            pattern_type=pattern_type,  # type: ignore
                            asset_id=a_id,
                            component_id=c_id,
                            occurrence_count=len(items),
                            affected_inspection_ids=insp_ids,
                            confidence="HIGH" if len(items) >= 3 else "MEDIUM",
                            explanation=explanation,
                            first_seen=min(timestamps),
                            last_seen=max(timestamps)
                        )
                    )

        _add_patterns(
            fp_buckets,
            "REPEATED_FALSE_POSITIVES",
            "Observed {count} recurring false positive defect detections on asset '{asset}'{comp}."
        )
        _add_patterns(
            fn_buckets,
            "REPEATED_FALSE_NEGATIVES",
            "Observed {count} missed defects (false negatives) confirmed by human reviewers on asset '{asset}'{comp}."
        )
        _add_patterns(
            over_buckets,
            "RECURRING_SEVERITY_OVERESTIMATION",
            "Observed {count} recurring severity overestimations by AI on asset '{asset}'{comp}."
        )
        _add_patterns(
            under_buckets,
            "RECURRING_SEVERITY_UNDERESTIMATION",
            "Observed {count} recurring severity underestimations by AI on asset '{asset}'{comp} requiring human elevation."
        )
        _add_patterns(
            action_buckets,
            "REPEATED_ACTION_DISAGREEMENT",
            "Observed {count} operational action modifications or rejections by human inspectors on asset '{asset}'{comp}."
        )

        return patterns


inspection_learning_service = InspectionLearningService()
