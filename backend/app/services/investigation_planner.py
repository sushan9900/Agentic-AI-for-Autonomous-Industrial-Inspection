"""Deterministic Agentic Investigation Planner (Phase 6C)."""

from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.inspection_history import HistoricalInspectionContext
from backend.app.schemas.inspection_trend import InspectionTrendAnalysis
from backend.app.schemas.investigation_plan import (
    CauseConfidenceLiteral,
    DiagnosticStep,
    EvidenceReference,
    EvidenceSufficiencyLiteral,
    HumanReviewPoint,
    InformationGap,
    InvestigationCause,
    InvestigationPlan,
    InvestigationPriorityLiteral,
)
from vision.schemas.evidence import VisionEvidence


class InvestigationPlanner:
    """
    Deterministic decision-support investigation planning engine.
    Derives structured diagnostic plans from authoritative evidence, risk scores,
    and historical/trend intelligence without performing automated maintenance.
    """

    @staticmethod
    def classify_priority(
        risk_score: int,
        severity: Optional[str],
        recurrence_pattern: str,
        deterioration_status: str
    ) -> InvestigationPriorityLiteral:
        """
        Computes deterministic investigation priority.
        These are investigation-planning priority tiers only and NEVER modify the authoritative decision.
        """
        sev_upper = (severity or "LOW").strip().upper()

        if (
            risk_score >= 80
            or (sev_upper == "CRITICAL" and deterioration_status == "DETERIORATING")
            or (recurrence_pattern in ("PERSISTENT", "RECURRENT") and sev_upper == "CRITICAL")
        ):
            return "CRITICAL"

        if (
            risk_score >= 60
            or deterioration_status == "DETERIORATING"
            or (recurrence_pattern in ("PERSISTENT", "RECURRENT") and sev_upper == "HIGH")
        ):
            return "HIGH"

        if (
            risk_score >= 40
            or recurrence_pattern in ("PERSISTENT", "RECURRENT")
        ):
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def generate_suspected_causes(
        defect_type: Optional[str],
        defect_count: int,
        severity: Optional[str],
        max_area: float,
        max_crack: float,
        recurrence_pattern: str,
        deterioration_status: str,
        source_ids: List[str]
    ) -> List[InvestigationCause]:
        """
        Generates evidence-grounded potential causes without speculating unobserved physical facts.
        """
        causes: List[InvestigationCause] = []
        d_type = defect_type or "defect"
        sev = (severity or "LOW").upper()

        if defect_count == 0:
            causes.append(
                InvestigationCause(
                    cause="No visible surface defects detected",
                    rationale="Vision model perception identified 0 defect indications above confidence threshold.",
                    confidence="HIGH",
                    supporting_evidence=["Detection count: 0"],
                    source_ids=source_ids
                )
            )
            return causes

        # 1. Progression cause
        if deterioration_status == "DETERIORATING" or defect_count >= 2:
            causes.append(
                InvestigationCause(
                    cause=f"Potential progressive {d_type} propagation under operational cyclic stress",
                    rationale=f"Multi-inspection trends report DETERIORATING status with {defect_count} defect indication(s).",
                    confidence="HIGH" if (max_area >= 5.0 or max_crack >= 200.0) else "MEDIUM",
                    supporting_evidence=[
                        f"Deterioration status: {deterioration_status}",
                        f"Detected count: {defect_count}",
                        f"Max affected area: {max_area:.2f}%",
                        f"Max crack length: {max_crack:.1f}px"
                    ],
                    source_ids=source_ids
                )
            )

        # 2. Recurrence cause
        if recurrence_pattern == "PERSISTENT":
            causes.append(
                InvestigationCause(
                    cause=f"Persistent unresolved {d_type} indication",
                    rationale=f"Identical defect classification '{d_type}' detected across consecutive chronological inspections.",
                    confidence="HIGH",
                    supporting_evidence=[f"Recurrence pattern: {recurrence_pattern}"],
                    source_ids=source_ids
                )
            )
        elif recurrence_pattern == "RECURRENT":
            causes.append(
                InvestigationCause(
                    cause=f"Intermittent {d_type} re-emergence following prior maintenance or clean interval",
                    rationale=f"Defect '{d_type}' re-emerged after prior clean inspection interval.",
                    confidence="MEDIUM",
                    supporting_evidence=[f"Recurrence pattern: {recurrence_pattern}"],
                    source_ids=source_ids
                )
            )

        # 3. High Severity / Localized Stress
        if sev in ("CRITICAL", "HIGH"):
            causes.append(
                InvestigationCause(
                    cause=f"Localized structural stress concentration or fatigue initiation ({d_type})",
                    rationale=f"Physical detection severity is {sev} with estimated crack length {max_crack:.1f}px.",
                    confidence="HIGH" if max_crack >= 100.0 else "MEDIUM",
                    supporting_evidence=[f"Severity: {sev}", f"Max crack length: {max_crack:.1f}px"],
                    source_ids=source_ids
                )
            )

        # 4. Fallback if no specific causes could be determined
        if not causes:
            causes.append(
                InvestigationCause(
                    cause=f"First-observed {d_type} indication requiring baseline establishment",
                    rationale="Initial observation without longitudinal precedent; cause requires field verification.",
                    confidence="LOW",
                    supporting_evidence=[f"Defect type: {d_type}", f"Severity: {sev}"],
                    source_ids=source_ids
                )
            )

        return causes

    @staticmethod
    def generate_diagnostic_steps(
        priority: str,
        defect_type: str,
        component_id: Optional[str],
        is_recurring: bool
    ) -> List[DiagnosticStep]:
        """
        Constructs safe, ordered, non-destructive diagnostic steps requiring human execution.
        """
        c_id = component_id or "target component"
        steps = [
            DiagnosticStep(
                step_number=1,
                action=f"Perform localized visual and optical magnification inspection on {c_id}.",
                purpose="Verify physical indication location, orientation, and surface morphology against visual bounding box.",
                expected_observation=f"Physical surface discontinuity corresponding to visual {defect_type} detection.",
                confirms_if="Surface fissure or crack matches detected bounding box coordinates.",
                weakens_if="Indication is identified as surface grime, oil streak, or optical reflection.",
                evidence_required=["Calibrated optical photograph", "Dimensional scale marker"],
                human_required=True
            ),
            DiagnosticStep(
                step_number=2,
                action="Cross-reference historical inspection records and imagery." if is_recurring else "Record baseline dimensional measurements for future longitudinal tracking.",
                purpose="Establish dimensional delta against prior records." if is_recurring else "Create initial dimensional baseline in asset register.",
                expected_observation="Defect dimensional comparison showing progression." if is_recurring else "Exact baseline length and width coordinates.",
                confirms_if="Defect propagation verified relative to prior inspection record.",
                weakens_if="Defect geometry is unchanged from original baseline manufacturing marks.",
                evidence_required=["Prior inspection records"] if is_recurring else ["Baseline dimensional log"],
                human_required=True
            ),
            DiagnosticStep(
                step_number=3,
                action="Perform Non-Destructive Examination (Liquid Penetrant or Ultrasonic Testing).",
                purpose="Determine subsurface crack depth and inspect for structural wall penetration.",
                expected_observation="Subsurface reflection or dye bleed demonstrating crack depth.",
                confirms_if="Subsurface penetration confirmed exceeding material tolerance.",
                weakens_if="Zero depth confirmed; superficial paint or coating scratch only.",
                evidence_required=["NDE examination report", "Ultrasonic A-scan / B-scan calibration logs"],
                human_required=True
            ),
            DiagnosticStep(
                step_number=4,
                action="Review operational load transients and pressure/thermal logs.",
                purpose="Assess whether cyclic pressure or thermal transients correlate with defect location.",
                expected_observation="Operational telemetry showing cyclic pressure spikes or thermal fluctuations.",
                confirms_if="Pressure or temperature transients recorded near defect location.",
                weakens_if="Operational envelope maintained strictly within nominal steady-state boundaries.",
                evidence_required=["SCADA telemetry export", "Operating logbook"],
                human_required=True
            ),
            DiagnosticStep(
                step_number=5,
                action="Submit diagnostic findings for Inspector Review Workstation authorization.",
                purpose="Mandatory human safety gate sign-off prior to maintenance scheduling or action.",
                expected_observation="Human inspector review status recorded as APPROVED or REJECTED.",
                confirms_if="Qualified inspector validates diagnostic findings.",
                weakens_if="Inspector rejects automated assessment based on in-person physical inspection.",
                evidence_required=["Inspector authorization signature / audit record"],
                human_required=True
            )
        ]
        return steps

    @staticmethod
    def identify_confirmation_signals(defect_type: str) -> Tuple[List[str], List[str]]:
        """Specifies observations that strengthen or weaken suspected causes."""
        d = defect_type.lower()
        confirmations = [
            f"Physical surface crack or {d} confirmed under optical magnification.",
            "Subsurface structural wall thinning or penetration verified via ultrasonic NDE.",
            "Defect dimensions exhibit measurable growth compared to historical baseline.",
            "Acoustic emission sensors detect active crack propagation under cyclic operational load."
        ]
        disconfirmations = [
            "Indication disappears upon surface cleaning or solvent wipe (superficial grease/dirt artifact).",
            "Zero depth confirmed by depth gauge (superficial protective coating scratch only).",
            "Defect dimensions remain identical to initial manufacturing fabrication baseline.",
            "Perception anomaly attributable to camera lens glare, uneven lighting, or shadow artifact."
        ]
        return confirmations, disconfirmations

    @staticmethod
    def identify_information_gaps(
        evidence_sufficiency: EvidenceSufficiencyLiteral,
        has_history: bool
    ) -> List[InformationGap]:
        """Identifies missing engineering parameters requiring human verification."""
        gaps = [
            InformationGap(
                field="Subsurface Defect Depth",
                reason="2D visual surface perception cannot measure volumetric penetration depth.",
                importance="CRITICAL",
                verification_method="Ultrasonic NDE testing (UT) or Eddy Current testing."
            ),
            InformationGap(
                field="Operational Load & Vibration History",
                reason="Static imagery lacks dynamic SCADA vibration, pressure, and cyclic stress data.",
                importance="HIGH",
                verification_method="Extract SCADA operating logs for the preceding 90 days."
            ),
            InformationGap(
                field="Material Metallurgy & Fabrication Tolerances",
                reason="Component material grade and allowable fracture toughness are not stored in image metadata.",
                importance="MEDIUM",
                verification_method="Review engineering asset specification drawing and heat treatment records."
            ),
            InformationGap(
                field="Environmental Chemical Exposure",
                reason="Corrosive chemical exposure or atmospheric salinity cannot be determined from imagery.",
                importance="LOW",
                verification_method="Review local environmental sensor telemetry or atmospheric logs."
            )
        ]
        if not has_history or evidence_sufficiency == "INSUFFICIENT":
            gaps.append(
                InformationGap(
                    field="Longitudinal Inspection Baseline",
                    reason="Historical inspection track record is insufficient (< 2 records) to establish rate of growth.",
                    importance="HIGH",
                    verification_method="Perform baseline dimensional survey and log initial coordinates."
                )
            )
        return gaps

    def generate_plan(
        self,
        inspection_id: str,
        asset_id: str,
        evidence: VisionEvidence,
        risk_score: int,
        operational_decision: str,
        component_id: Optional[str] = None,
        historical_context: Optional[HistoricalInspectionContext] = None,
        trends: Optional[InspectionTrendAnalysis] = None
    ) -> InvestigationPlan:
        """
        Orchestrates deterministic investigation plan generation.
        Strictly decision-support only: authoritative = False.
        """
        try:
            # 1. Primary defect extraction
            defect_type = "crack"
            defect_count = len(evidence.detections)
            max_area = 0.0
            max_crack = 0.0
            severity = "LOW"

            if evidence.detections:
                d0 = evidence.detections[0]
                defect_type = d0.defect_type.value if hasattr(d0.defect_type, "value") else str(d0.defect_type)
                max_area = max([getattr(d.severity_features, "affected_area_percentage", 0.0) or 0.0 for d in evidence.detections if d.severity_features], default=0.0)
                max_crack = max([getattr(d.severity_features, "crack_length_pixels", 0.0) or 0.0 for d in evidence.detections if d.severity_features], default=0.0)

                if max_crack >= 200.0 or max_area >= 10.0:
                    severity = "CRITICAL"
                elif max_crack >= 100.0 or max_area >= 5.0:
                    severity = "HIGH"
                elif max_crack >= 30.0 or max_area >= 2.0:
                    severity = "MEDIUM"

            # 2. Historical & trend intelligence
            has_history = historical_context.has_history if historical_context else False
            rec_pattern = trends.recurrence_pattern if trends else "INSUFFICIENT_HISTORY"
            det_status = trends.deterioration_status if trends else "INSUFFICIENT_HISTORY"
            suff_tier = trends.evidence_sufficiency if trends else ("LIMITED" if has_history else "INSUFFICIENT")
            source_ids = trends.source_inspection_ids if trends else []

            # 3. Deterministic Priority
            priority = self.classify_priority(
                risk_score=risk_score,
                severity=severity,
                recurrence_pattern=rec_pattern,
                deterioration_status=det_status
            )

            # 4. Suspected causes
            suspected_causes = self.generate_suspected_causes(
                defect_type=defect_type,
                defect_count=defect_count,
                severity=severity,
                max_area=max_area,
                max_crack=max_crack,
                recurrence_pattern=rec_pattern,
                deterioration_status=det_status,
                source_ids=source_ids
            )

            # 5. Diagnostic steps
            is_rec = rec_pattern in ("PERSISTENT", "RECURRENT")
            diagnostic_steps = self.generate_diagnostic_steps(
                priority=priority,
                defect_type=defect_type,
                component_id=component_id,
                is_recurring=is_rec
            )

            # 6. Confirmation / Disconfirmation signals
            confirm_signals, disconfirm_signals = self.identify_confirmation_signals(defect_type)

            # 7. Information Gaps
            gaps = self.identify_information_gaps(suff_tier, has_history)

            # 8. Evidence Basis
            evidence_basis = [
                EvidenceReference(
                    reference_type="VISUAL_DETECTION",
                    reference_id=inspection_id,
                    description=f"{defect_count} defect(s) detected (type='{defect_type}', max_crack={max_crack:.1f}px, max_area={max_area:.2f}%)."
                ),
                EvidenceReference(
                    reference_type="AUTHORITATIVE_DECISION",
                    reference_id=f"dec-{inspection_id}-{asset_id}",
                    description=f"Risk Score: {risk_score}/100, Operational Decision: '{operational_decision}'."
                )
            ]
            if trends:
                evidence_basis.append(
                    EvidenceReference(
                        reference_type="TREND_ANALYSIS",
                        reference_id=f"trends-{asset_id}",
                        description=f"Deterioration: {det_status}, Recurrence: {rec_pattern}, Trend: {trends.risk_trend}."
                    )
                )

            historical_basis = []
            if historical_context and historical_context.summary:
                historical_basis.append(
                    f"Total prior inspections: {historical_context.summary.total_previous_inspections}, "
                    f"Risk trend: {historical_context.summary.risk_trend}, "
                    f"Recurring defect: {historical_context.summary.recurring_defect_detected}."
                )

            trend_basis = []
            if trends:
                trend_basis.append(
                    f"Deterioration status: {trends.deterioration_status}, "
                    f"Defect progression: {trends.defect_trend}, "
                    f"Severity progression: {trends.severity_trend}."
                )

            human_review_points = [
                HumanReviewPoint(
                    checkpoint="Inspect visual indication boundaries against physical component",
                    reason="Verify model perception against true surface condition"
                ),
                HumanReviewPoint(
                    checkpoint="Review and confirm NDE examination requirement before technician dispatch",
                    reason="Ensure physical testing is safe and justified under site operating constraints"
                ),
                HumanReviewPoint(
                    checkpoint="Final disposition sign-off in Inspector Review Workstation",
                    reason="Authoritative human safety gate requirement"
                )
            ]

            plan_id = f"plan-{inspection_id}-{asset_id}"

            return InvestigationPlan(
                plan_id=plan_id,
                inspection_id=inspection_id,
                asset_id=asset_id,
                component_id=component_id,
                priority=priority,
                objective=f"Diagnose physical integrity and evaluate progression of {defect_type} on asset '{asset_id}'.",
                primary_question=f"Does the detected {defect_type} represent an active structural wall breach or progressive fatigue failure?",
                suspected_causes=suspected_causes,
                diagnostic_steps=diagnostic_steps,
                evidence_basis=evidence_basis,
                historical_basis=historical_basis,
                trend_basis=trend_basis,
                information_gaps=gaps,
                confirmation_signals=confirm_signals,
                disconfirmation_signals=disconfirm_signals,
                human_review_points=human_review_points,
                constraints=[
                    "Decision support only: zero automated maintenance execution.",
                    "Zero plant-control modification or PLC/SCADA override.",
                    "Mandatory human sign-off required prior to technician dispatch."
                ],
                safety_notes=[
                    "Ensure line depressurization if wall breach is suspected.",
                    "Follow standard site Lockout/Tagout (LOTO) protocols during physical examination."
                ],
                evidence_sufficiency=suff_tier,
                source_inspection_ids=source_ids,
                generated_by="deterministic_investigation_planner_v1",
                authoritative=False
            )

        except Exception as e:
            # Safe non-crashing fallback
            return InvestigationPlan(
                plan_id=f"plan-{inspection_id}-{asset_id}-fallback",
                inspection_id=inspection_id,
                asset_id=asset_id,
                component_id=component_id,
                priority="CRITICAL" if risk_score >= 80 else ("HIGH" if risk_score >= 60 else "MEDIUM"),
                objective="Conduct field visual inspection due to automated planning degradation.",
                primary_question="What is the actual physical condition of the component?",
                suspected_causes=[
                    InvestigationCause(
                        cause="UNKNOWN",
                        rationale=f"Investigation planner degraded safely: {e}",
                        confidence="LOW",
                        supporting_evidence=[],
                        source_ids=[]
                    )
                ],
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        action="Perform visual verification of component.",
                        purpose="Manual physical inspection.",
                        expected_observation="Inspector field observations.",
                        confirms_if="Inspector confirms defect.",
                        weakens_if="Inspector rejects defect.",
                        evidence_required=["Inspector notes"],
                        human_required=True
                    )
                ],
                evidence_basis=[],
                historical_basis=[],
                trend_basis=[],
                information_gaps=[],
                confirmation_signals=[],
                disconfirmation_signals=[],
                human_review_points=[
                    HumanReviewPoint(
                        checkpoint="Manual inspector verification required",
                        reason="Automated planner degraded safely",
                        required=True
                    )
                ],
                safety_notes=["Follow site safety procedures."],
                evidence_sufficiency="INSUFFICIENT",
                source_inspection_ids=[],
                generated_by="deterministic_investigation_planner_fallback",
                authoritative=False
            )


investigation_planner = InvestigationPlanner()
