"""Deterministic Inspection Timing Recommendation Service (Phase 8D)."""

from typing import List, Optional
from backend.app.schemas.inspection_task import TimingWindow
from backend.app.schemas.inspection_timing import TimingRecommendation


class InspectionTimingService:
    """
    Deterministic evaluation service calculating recommended inspection timing windows.
    Strictly advisory. No LLM used for scheduling window decisions.
    """

    def evaluate_timing(
        self,
        risk_score: int,
        severity: str,
        deterioration_status: Optional[str] = None,
        recurrence_pattern: Optional[str] = None,
        review_age_hours: Optional[float] = None
    ) -> TimingRecommendation:
        """
        Calculates recommended timing window based on deterministic multi-factor rules.
        """
        sev_upper = (severity or "LOW").strip().upper()
        det_upper = (deterioration_status or "UNKNOWN").strip().upper()
        rec_upper = (recurrence_pattern or "UNKNOWN").strip().upper()

        factors: List[str] = []

        # Rule 1: CRITICAL + Deteriorating -> IMMEDIATE
        if (risk_score >= 80 or sev_upper == "CRITICAL") and det_upper == "DETERIORATING":
            factors.append("Critical risk severity combined with active deterioration trend")
            return TimingRecommendation(
                timing_window=TimingWindow.IMMEDIATE,
                urgency="CRITICAL",
                rationale="Critical structural risk with documented physical deterioration warrants immediate inspection.",
                supporting_factors=factors,
                authoritative=False
            )

        # Rule 2: CRITICAL (stable) OR HIGH + Deteriorating -> WITHIN_24_HOURS
        if (risk_score >= 80 or sev_upper == "CRITICAL") or (risk_score >= 60 and det_upper == "DETERIORATING"):
            factors.append(f"Elevated risk score ({risk_score}/100) requires expedited examination")
            if det_upper == "DETERIORATING":
                factors.append("Active deterioration trend observed across historical inspections")
            return TimingRecommendation(
                timing_window=TimingWindow.WITHIN_24_HOURS,
                urgency="HIGH",
                rationale="Elevated defect severity or accelerating trend warrants field inspection within 24 hours.",
                supporting_factors=factors,
                authoritative=False
            )

        # Rule 3: HIGH risk OR Persistent recurrence -> WITHIN_7_DAYS
        if risk_score >= 60 or sev_upper == "HIGH" or rec_upper in ("PERSISTENT", "RECURRENT"):
            if risk_score >= 60 or sev_upper == "HIGH":
                factors.append("High defect severity classification")
            if rec_upper in ("PERSISTENT", "RECURRENT"):
                factors.append(f"Historical recurrence pattern: {rec_upper}")
            return TimingRecommendation(
                timing_window=TimingWindow.WITHIN_7_DAYS,
                urgency="MEDIUM",
                rationale="Significant defect risk or recurring defect behavior warrants inspection within 7 days.",
                supporting_factors=factors,
                authoritative=False
            )

        # Rule 4: MODERATE / MEDIUM risk -> WITHIN_30_DAYS
        if risk_score >= 40 or sev_upper in ("MEDIUM", "MODERATE"):
            factors.append(f"Moderate baseline risk ({risk_score}/100)")
            return TimingRecommendation(
                timing_window=TimingWindow.WITHIN_30_DAYS,
                urgency="LOW",
                rationale="Moderate defect severity with stable progression warrants inspection within standard monthly cycle.",
                supporting_factors=factors,
                authoritative=False
            )

        # Rule 5: Nominal / Low risk -> ROUTINE
        factors.append(f"Nominal asset condition (risk: {risk_score}/100)")
        return TimingRecommendation(
            timing_window=TimingWindow.ROUTINE,
            urgency="LOW",
            rationale="Defect state is nominal or absent; standard scheduled routine inspection interval recommended.",
            supporting_factors=factors,
            authoritative=False
        )


inspection_timing_service = InspectionTimingService()
