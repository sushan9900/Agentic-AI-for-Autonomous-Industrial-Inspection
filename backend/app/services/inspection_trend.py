"""Deterministic Multi-Inspection Trend Analysis Engine (Phase 6B)."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.inspection_history import HistoricalInspectionRecord
from backend.app.schemas.inspection_trend import (
    DefectObservationPoint,
    DeteriorationStatusLiteral,
    EvidenceSufficiencyLiteral,
    FrequencyTrendLiteral,
    InspectionIntervalPoint,
    InspectionTrendAnalysis,
    ProgressionTrendLiteral,
    RecurrencePatternLiteral,
    RiskScoreObservationPoint,
    SeverityObservationPoint,
)

logger = logging.getLogger(__name__)


class InspectionTrendService:
    """Deterministic, mathematical trend analysis engine across chronological inspection series."""

    SEVERITY_RANKS: Dict[str, int] = {
        "LOW": 1,
        "MEDIUM": 2,
        "MODERATE": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    def build_time_series(
        self,
        records: List[HistoricalInspectionRecord],
        decisions: List[Dict[str, Any]]
    ) -> Tuple[
        List[DefectObservationPoint],
        List[SeverityObservationPoint],
        List[RiskScoreObservationPoint],
        List[InspectionIntervalPoint]
    ]:
        """
        Constructs chronological time-series observations from historical records and decisions.
        Ensures strict source traceability and chronological ordering.
        """
        # Sort records chronologically (oldest first)
        valid_records = [r for r in records if r.inspection_timestamp is not None]
        sorted_records = sorted(valid_records, key=lambda x: x.inspection_timestamp)

        defect_series: List[DefectObservationPoint] = []
        severity_series: List[SeverityObservationPoint] = []
        seen_insp_ids = set()

        for r in sorted_records:
            if r.inspection_id in seen_insp_ids:
                continue
            seen_insp_ids.add(r.inspection_id)

            # Defect observation
            if r.defect_type:
                defect_series.append(
                    DefectObservationPoint(
                        timestamp=r.inspection_timestamp,
                        inspection_id=r.inspection_id,
                        defect_type=r.defect_type,
                        defect_count=1,
                        source_record_id=r.source_record_id
                    )
                )

            # Severity observation
            if r.severity:
                sev_upper = r.severity.strip().upper()
                rank = self.SEVERITY_RANKS.get(sev_upper, 1)
                severity_series.append(
                    SeverityObservationPoint(
                        timestamp=r.inspection_timestamp,
                        inspection_id=r.inspection_id,
                        severity=sev_upper,
                        severity_rank=rank,
                        source_record_id=r.source_record_id
                    )
                )

        # Build risk score series from decisions (oldest first)
        valid_decisions = []
        for d in decisions:
            created_at_raw = d.get("created_at")
            if created_at_raw and d.get("risk_score") is not None:
                try:
                    dt = datetime.fromisoformat(created_at_raw) if isinstance(created_at_raw, str) else created_at_raw
                    valid_decisions.append({**d, "_dt": dt})
                except Exception:
                    continue

        sorted_decisions = sorted(valid_decisions, key=lambda x: x["_dt"])
        risk_series: List[RiskScoreObservationPoint] = []
        for d in sorted_decisions:
            risk_series.append(
                RiskScoreObservationPoint(
                    timestamp=d["_dt"],
                    inspection_id=d.get("inspection_id", "UNKNOWN"),
                    risk_score=int(d["risk_score"]),
                    risk_level=d.get("risk_level", "LOW").upper(),
                    source_record_id=d.get("decision_id", "UNKNOWN")
                )
            )

        # Build interval series between consecutive inspection records
        interval_series: List[InspectionIntervalPoint] = []
        for i in range(len(sorted_records) - 1):
            t0 = sorted_records[i].inspection_timestamp
            t1 = sorted_records[i + 1].inspection_timestamp
            delta_days = round((t1 - t0).total_seconds() / 86400.0, 2)
            interval_series.append(
                InspectionIntervalPoint(
                    from_inspection_id=sorted_records[i].inspection_id,
                    to_inspection_id=sorted_records[i + 1].inspection_id,
                    interval_days=max(0.0, delta_days)
                )
            )

        return defect_series, severity_series, risk_series, interval_series

    def analyze_defect_progression(
        self,
        defect_series: List[DefectObservationPoint]
    ) -> Tuple[ProgressionTrendLiteral, str]:
        """
        Evaluates defect count/burden progression chronologically.
        Requires at least 2 valid observations.
        """
        if len(defect_series) < 2:
            return (
                "INSUFFICIENT_HISTORY",
                "Fewer than 2 valid defect observations available."
            )

        earliest = defect_series[0]
        latest = defect_series[-1]
        delta_count = latest.defect_count - earliest.defect_count

        if delta_count > 0:
            return (
                "INCREASING",
                f"Defect count increased from {earliest.defect_count} to {latest.defect_count} across {len(defect_series)} inspections."
            )
        elif delta_count < 0:
            return (
                "DECREASING",
                f"Defect count decreased from {earliest.defect_count} to {latest.defect_count} across {len(defect_series)} inspections."
            )
        else:
            return (
                "STABLE",
                f"Defect count remained consistent at {latest.defect_count} across {len(defect_series)} inspections."
            )

    def analyze_severity_progression(
        self,
        severity_series: List[SeverityObservationPoint]
    ) -> Tuple[ProgressionTrendLiteral, str]:
        """
        Evaluates physical severity progression using ordinal severity ranking.
        LOW (1) < MEDIUM (2) < HIGH (3) < CRITICAL (4).
        Requires at least 2 valid observations.
        """
        if len(severity_series) < 2:
            return (
                "INSUFFICIENT_HISTORY",
                "Fewer than 2 valid severity observations available."
            )

        earliest = severity_series[0]
        latest = severity_series[-1]
        delta_rank = latest.severity_rank - earliest.severity_rank

        if delta_rank > 0:
            return (
                "INCREASING",
                f"Severity progressed from {earliest.severity} (Rank {earliest.severity_rank}) to {latest.severity} (Rank {latest.severity_rank})."
            )
        elif delta_rank < 0:
            return (
                "DECREASING",
                f"Severity improved from {earliest.severity} (Rank {earliest.severity_rank}) to {latest.severity} (Rank {latest.severity_rank})."
            )
        else:
            return (
                "STABLE",
                f"Severity remained stable at {latest.severity} (Rank {latest.severity_rank}) across {len(severity_series)} inspections."
            )

    def analyze_risk_trajectory(
        self,
        risk_series: List[RiskScoreObservationPoint]
    ) -> Tuple[ProgressionTrendLiteral, str]:
        """
        Evaluates authoritative risk score trajectory.
        Delta >= +10: INCREASING, Delta <= -10: DECREASING, otherwise STABLE.
        """
        if len(risk_series) < 2:
            return (
                "INSUFFICIENT_HISTORY",
                "Fewer than 2 valid authoritative risk assessments exist for trajectory analysis."
            )

        earliest = risk_series[0]
        latest = risk_series[-1]
        delta = latest.risk_score - earliest.risk_score

        if delta >= 10:
            return (
                "INCREASING",
                f"Authoritative risk score increased by {delta} points (from {earliest.risk_score} to {latest.risk_score})."
            )
        elif delta <= -10:
            return (
                "DECREASING",
                f"Authoritative risk score decreased by {abs(delta)} points (from {earliest.risk_score} to {latest.risk_score})."
            )
        else:
            scores = [p.risk_score for p in risk_series]
            return (
                "STABLE",
                f"Authoritative risk score remained stable within +/- 10 points (ranging {min(scores)} to {max(scores)})."
            )

    def analyze_recurrence_pattern(
        self,
        records: List[HistoricalInspectionRecord],
        target_defect: Optional[str]
    ) -> Tuple[RecurrencePatternLiteral, int, str]:
        """
        Analyzes whether a defect is PERSISTENT (consecutive), RECURRENT (intermittent), or NO_RECURRENCE.
        """
        if not records or len(records) < 2 or not target_defect:
            return (
                "INSUFFICIENT_HISTORY",
                0,
                "Fewer than 2 records or missing defect classification for recurrence analysis."
            )

        term = target_defect.strip().lower()
        # Sort chronologically
        valid_records = [r for r in records if r.inspection_timestamp is not None]
        sorted_records = sorted(valid_records, key=lambda x: x.inspection_timestamp)

        presence_flags: List[bool] = []
        for r in sorted_records:
            is_present = bool(r.defect_type and term in r.defect_type.lower())
            presence_flags.append(is_present)

        count = sum(presence_flags)
        if count == 0:
            return ("NO_RECURRENCE", 0, f"Defect '{target_defect}' was not detected in prior inspections.")
        elif count == 1:
            return ("NO_RECURRENCE", 1, f"Defect '{target_defect}' detected only once; no recurrence pattern.")

        # Check consecutive presence
        indices = [i for i, present in enumerate(presence_flags) if present]
        consecutive = True
        for j in range(len(indices) - 1):
            if indices[j + 1] != indices[j] + 1:
                consecutive = False
                break

        if consecutive:
            return (
                "PERSISTENT",
                count,
                f"Defect '{target_defect}' detected across {count} consecutive chronological inspections."
            )
        else:
            return (
                "RECURRENT",
                count,
                f"Defect '{target_defect}' reoccurred across {count} non-consecutive inspections with intermediate absence."
            )

    def analyze_inspection_intervals(
        self,
        interval_series: List[InspectionIntervalPoint]
    ) -> Tuple[Optional[float], Optional[float], Optional[float], FrequencyTrendLiteral, str]:
        """
        Computes inspection intervals, summary statistics, and frequency velocity trend.
        """
        if not interval_series:
            return (
                None,
                None,
                None,
                "INSUFFICIENT_HISTORY",
                "Fewer than 2 chronological timestamps available for interval analysis."
            )

        intervals = [p.interval_days for p in interval_series]
        avg_int = round(sum(intervals) / len(intervals), 2)
        min_int = round(min(intervals), 2)
        max_int = round(max(intervals), 2)

        if len(intervals) >= 2:
            recent = intervals[-1]
            prior_avg = sum(intervals[:-1]) / len(intervals[:-1])
            if recent <= 0.75 * prior_avg:
                trend: FrequencyTrendLiteral = "FREQUENCY_INCREASING"
                expl = f"Inspection frequency increasing: recent interval ({recent:.1f}d) is significantly shorter than prior average ({prior_avg:.1f}d)."
            elif recent >= 1.35 * prior_avg:
                trend = "FREQUENCY_DECREASING"
                expl = f"Inspection frequency decreasing: recent interval ({recent:.1f}d) is longer than prior average ({prior_avg:.1f}d)."
            else:
                trend = "FREQUENCY_STABLE"
                expl = f"Inspection interval is stable (average: {avg_int:.1f} days across {len(intervals)} intervals)."
        else:
            trend = "FREQUENCY_STABLE"
            expl = f"Single inspection interval recorded ({avg_int:.1f} days)."

        return avg_int, min_int, max_int, trend, expl

    def evaluate_evidence_sufficiency(
        self,
        inspection_count: int,
        defect_obs_count: int,
        risk_obs_count: int
    ) -> EvidenceSufficiencyLiteral:
        """Determines evidence confidence tier for longitudinal trend reliability."""
        if inspection_count >= 3 and (defect_obs_count >= 2 or risk_obs_count >= 2):
            return "SUFFICIENT"
        elif inspection_count == 2:
            return "LIMITED"
        else:
            return "INSUFFICIENT"

    def evaluate_deterioration_status(
        self,
        evidence_sufficiency: EvidenceSufficiencyLiteral,
        defect_trend: ProgressionTrendLiteral,
        severity_trend: ProgressionTrendLiteral,
        risk_trend: ProgressionTrendLiteral,
        recurrence_pattern: RecurrencePatternLiteral,
        latest_risk_score: Optional[int]
    ) -> Tuple[DeteriorationStatusLiteral, str]:
        """
        Transparent deterministic synthesis of multi-signal deterioration status.
        Never relies on LLM or opaque scoring.
        """
        if evidence_sufficiency == "INSUFFICIENT":
            return (
                "INSUFFICIENT_HISTORY",
                "Evidence sufficiency is INSUFFICIENT (< 2 historical records)."
            )

        # Deterioration condition: any key indicator worsening without improvement
        worsening = [
            t == "INCREASING"
            for t in (defect_trend, severity_trend, risk_trend)
        ]
        improving = [
            t == "DECREASING"
            for t in (defect_trend, severity_trend, risk_trend)
        ]

        if any(worsening) and not any(improving):
            signals = []
            if defect_trend == "INCREASING":
                signals.append("defect burden")
            if severity_trend == "INCREASING":
                signals.append("severity")
            if risk_trend == "INCREASING":
                signals.append("risk score")
            return (
                "DETERIORATING",
                f"Multi-signal deterioration observed: {' and '.join(signals)} progressing upward."
            )

        if any(improving) and not any(worsening):
            return (
                "IMPROVING",
                "Positive condition trend observed: defect burden and/or severity improving."
            )

        if recurrence_pattern in ("PERSISTENT", "RECURRENT") and (latest_risk_score is not None and latest_risk_score >= 60):
            return (
                "RECURRENT_RISK",
                f"Recurrent or persistent defect detected under elevated risk baseline ({latest_risk_score}/100)."
            )

        return (
            "STABLE",
            "Longitudinal indicators demonstrate stable condition within defined operational tolerances."
        )

    def analyze_trends(
        self,
        records: List[HistoricalInspectionRecord],
        decisions: List[Dict[str, Any]],
        asset_id: str,
        component_id: Optional[str] = None,
        defect_type: Optional[str] = None
    ) -> InspectionTrendAnalysis:
        """
        Master entrypoint orchestrating deterministic multi-inspection time series analysis.
        Guarantees fail-safe non-crashing execution.
        """
        try:
            # 1. Build chronological time series
            def_series, sev_series, rsk_series, int_series = self.build_time_series(
                records=records,
                decisions=decisions
            )

            # 2. Window metrics
            valid_records = [r for r in records if r.inspection_timestamp is not None]
            insp_count = len(valid_records)
            earliest_id = valid_records[-1].inspection_id if valid_records else None
            latest_id = valid_records[0].inspection_id if valid_records else None

            window_days = None
            if len(valid_records) >= 2:
                t_min = min(r.inspection_timestamp for r in valid_records)
                t_max = max(r.inspection_timestamp for r in valid_records)
                window_days = round((t_max - t_min).total_seconds() / 86400.0, 2)

            # 3. Independent progression trends
            defect_trend, def_expl = self.analyze_defect_progression(def_series)
            severity_trend, sev_expl = self.analyze_severity_progression(sev_series)
            risk_trend, rsk_expl = self.analyze_risk_trajectory(rsk_series)

            # 4. Recurrence analysis
            recurrence_pattern, rec_count, rec_expl = self.analyze_recurrence_pattern(
                records=records,
                target_defect=defect_type
            )

            # 5. Inspection frequency analysis
            avg_int, min_int, max_int, freq_trend, freq_expl = self.analyze_inspection_intervals(int_series)

            # 6. Evidence sufficiency & Deterioration status
            sufficiency = self.evaluate_evidence_sufficiency(
                inspection_count=insp_count,
                defect_obs_count=len(def_series),
                risk_obs_count=len(rsk_series)
            )

            latest_risk = rsk_series[-1].risk_score if rsk_series else None
            det_status, det_expl = self.evaluate_deterioration_status(
                evidence_sufficiency=sufficiency,
                defect_trend=defect_trend,
                severity_trend=severity_trend,
                risk_trend=risk_trend,
                recurrence_pattern=recurrence_pattern,
                latest_risk_score=latest_risk
            )

            source_ids = list(dict.fromkeys([r.inspection_id for r in valid_records]))

            explanation = (
                f"Deterioration Status: {det_status}. {det_expl} "
                f"Defect progression: {defect_trend}. Severity progression: {severity_trend}. "
                f"Risk trajectory: {risk_trend}. Recurrence: {recurrence_pattern}."
            )

            return InspectionTrendAnalysis(
                asset_id=asset_id,
                component_id=component_id,
                inspection_count=insp_count,
                earliest_inspection=earliest_id,
                latest_inspection=latest_id,
                analysis_window_days=window_days,
                defect_series=def_series,
                severity_series=sev_series,
                risk_series=rsk_series,
                interval_series=int_series,
                average_interval_days=avg_int,
                minimum_interval_days=min_int,
                maximum_interval_days=max_int,
                frequency_trend=freq_trend,
                defect_trend=defect_trend,
                severity_trend=severity_trend,
                risk_trend=risk_trend,
                recurrence_pattern=recurrence_pattern,
                recurrence_count=rec_count,
                deterioration_status=det_status,
                evidence_sufficiency=sufficiency,
                source_inspection_ids=source_ids,
                trend_summary_explanation=explanation,
                calculation_metadata={
                    "status": "SUCCESS",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "defect_observations_count": len(def_series),
                    "severity_observations_count": len(sev_series),
                    "risk_assessments_count": len(rsk_series),
                    "interval_measurements_count": len(int_series)
                }
            )

        except Exception as e:
            logger.warning(f"Inspection trend analysis degraded safely: {e}")
            return InspectionTrendAnalysis(
                asset_id=asset_id,
                component_id=component_id,
                inspection_count=0,
                trend_summary_explanation=f"Trend analysis safely degraded due to error: {e}",
                calculation_metadata={"status": "ERROR", "error": str(e)}
            )


inspection_trend_service = InspectionTrendService()
