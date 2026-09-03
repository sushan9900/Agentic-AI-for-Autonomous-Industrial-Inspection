"""Deterministic Agentic Inspection Prioritization & Scheduling Service (Phase 6D)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.schemas.inspection_prioritization import (
    InspectionPriorityItem,
    InspectionPriorityQueue,
    PriorityClassLiteral,
)


class InspectionPrioritizationService:
    """
    Deterministic prioritization service for ranking pending inspections for human engineering review.
    Calculates transparent review priority scores and deterministic ranking without executing maintenance.
    """

    METHODOLOGY_VERSION = "1.0"
    ACTIVE_PENDING_STATUSES = {"PENDING_HUMAN_REVIEW", "IN_REVIEW", "REVISION_REQUESTED"}

    @staticmethod
    def calculate_priority_score(
        risk_score: int,
        severity: Optional[str],
        deterioration_status: Optional[str],
        recurrence_pattern: Optional[str],
        evidence_sufficiency: Optional[str],
        investigation_priority: Optional[str],
        pending_age_hours: Optional[float]
    ) -> Tuple[int, List[str]]:
        """
        Computes the deterministic derived review priority score (0-100 pts) and contributing factor breakdown.
        Weights:
          - Risk component: max 40
          - Severity component: max 20
          - Deterioration component: max 15
          - Recurrence component: max 10
          - Evidence sufficiency: max 5
          - Investigation priority: max 5
          - Review age: max 5
        """
        factors: List[str] = []

        # 1. Risk Component (max 40)
        if risk_score >= 80:
            risk_pts = 40
            factors.append(f"Authoritative Risk >= 80 (+{risk_pts} pts)")
        elif risk_score >= 60:
            risk_pts = 30
            factors.append(f"Authoritative Risk >= 60 (+{risk_pts} pts)")
        elif risk_score >= 40:
            risk_pts = 20
            factors.append(f"Authoritative Risk >= 40 (+{risk_pts} pts)")
        else:
            risk_pts = 10
            factors.append(f"Authoritative Risk < 40 (+{risk_pts} pts)")

        # 2. Severity Component (max 20)
        sev_upper = (severity or "").strip().upper()
        if sev_upper == "CRITICAL":
            sev_pts = 20
            factors.append(f"Physical Severity CRITICAL (+{sev_pts} pts)")
        elif sev_upper == "HIGH":
            sev_pts = 15
            factors.append(f"Physical Severity HIGH (+{sev_pts} pts)")
        elif sev_upper in ("MEDIUM", "MODERATE"):
            sev_pts = 10
            factors.append(f"Physical Severity {sev_upper} (+{sev_pts} pts)")
        elif sev_upper == "LOW":
            sev_pts = 5
            factors.append(f"Physical Severity LOW (+{sev_pts} pts)")
        else:
            sev_pts = 0
            factors.append("Physical Severity UNKNOWN (+0 pts)")

        # 3. Deterioration Component (max 15)
        det_upper = (deterioration_status or "").strip().upper()
        if det_upper == "DETERIORATING":
            det_pts = 15
            factors.append(f"Multi-Inspection Trend DETERIORATING (+{det_pts} pts)")
        elif det_upper == "STABLE":
            det_pts = 5
            factors.append(f"Multi-Inspection Trend STABLE (+{det_pts} pts)")
        elif det_upper == "IMPROVING":
            det_pts = 0
            factors.append("Multi-Inspection Trend IMPROVING (+0 pts)")
        else:
            det_pts = 0
            factors.append("Multi-Inspection Trend INSUFFICIENT/UNKNOWN (+0 pts)")

        # 4. Recurrence Component (max 10)
        rec_upper = (recurrence_pattern or "").strip().upper()
        if rec_upper == "PERSISTENT":
            rec_pts = 10
            factors.append(f"Historical Defect PERSISTENT (+{rec_pts} pts)")
        elif rec_upper == "RECURRENT":
            rec_pts = 8
            factors.append(f"Historical Defect RECURRENT (+{rec_pts} pts)")
        elif rec_upper == "NO_RECURRENCE":
            rec_pts = 2
            factors.append(f"Historical Defect NO_RECURRENCE (+{rec_pts} pts)")
        else:
            rec_pts = 0
            factors.append("Historical Defect INSUFFICIENT/UNKNOWN (+0 pts)")

        # 5. Evidence Sufficiency (max 5)
        ev_upper = (evidence_sufficiency or "").strip().upper()
        if ev_upper == "SUFFICIENT":
            ev_pts = 5
            factors.append(f"Evidence Sufficiency SUFFICIENT (+{ev_pts} pts)")
        elif ev_upper == "LIMITED":
            ev_pts = 3
            factors.append(f"Evidence Sufficiency LIMITED (+{ev_pts} pts)")
        elif ev_upper == "INSUFFICIENT":
            ev_pts = 1
            factors.append(f"Evidence Sufficiency INSUFFICIENT (+{ev_pts} pts)")
        else:
            ev_pts = 0
            factors.append("Evidence Sufficiency UNKNOWN (+0 pts)")

        # 6. Investigation Priority (max 5)
        inv_upper = (investigation_priority or "").strip().upper()
        if inv_upper == "CRITICAL":
            inv_pts = 5
            factors.append(f"Investigation Priority CRITICAL (+{inv_pts} pts)")
        elif inv_upper == "HIGH":
            inv_pts = 4
            factors.append(f"Investigation Priority HIGH (+{inv_pts} pts)")
        elif inv_upper == "MEDIUM":
            inv_pts = 3
            factors.append(f"Investigation Priority MEDIUM (+{inv_pts} pts)")
        elif inv_upper == "LOW":
            inv_pts = 1
            factors.append(f"Investigation Priority LOW (+{inv_pts} pts)")
        else:
            inv_pts = 0
            factors.append("Investigation Priority UNKNOWN (+0 pts)")

        # 7. Pending Review Age (max 5)
        if pending_age_hours is not None:
            if pending_age_hours >= 72.0:
                age_pts = 5
            elif pending_age_hours >= 48.0:
                age_pts = 4
            elif pending_age_hours >= 24.0:
                age_pts = 3
            elif pending_age_hours >= 12.0:
                age_pts = 2
            elif pending_age_hours >= 1.0:
                age_pts = 1
            else:
                age_pts = 0
            factors.append(f"Pending Review Age {pending_age_hours:.1f}h (+{age_pts} pts)")
        else:
            age_pts = 0
            factors.append("Review age unavailable (+0 pts)")

        total = risk_pts + sev_pts + det_pts + rec_pts + ev_pts + inv_pts + age_pts
        return min(100, max(0, total)), factors

    @staticmethod
    def classify_priority(score: int) -> PriorityClassLiteral:
        """Maps derived priority score onto human review priority class."""
        if score >= 80:
            return "CRITICAL"
        if score >= 60:
            return "HIGH"
        if score >= 40:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def build_rationale(
        priority_class: str,
        priority_score: int,
        risk_score: int,
        severity: str,
        deterioration_status: Optional[str],
        recurrence_pattern: Optional[str]
    ) -> str:
        """Constructs concise, evidence-grounded human review rationale."""
        det_str = f", trend is {deterioration_status}" if deterioration_status and deterioration_status != "INSUFFICIENT_HISTORY" else ""
        rec_str = f", defect is {recurrence_pattern}" if recurrence_pattern and recurrence_pattern != "INSUFFICIENT_HISTORY" else ""
        return (
            f"{priority_class} review priority (score {priority_score}/100) because authoritative risk is {risk_score}/100, "
            f"physical severity is {severity}{det_str}{rec_str}."
        )

    def get_prioritized_queue(
        self,
        db: Session,
        status_filter: Optional[str] = "PENDING_HUMAN_REVIEW",
        priority_class: Optional[str] = None,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None,
        limit: int = 50
    ) -> InspectionPriorityQueue:
        """
        Queries pending decisions in a single batch query, calculates deterministic review priority,
        breaks ties deterministically, and formats the prioritized queue.
        Zero N+1 queries.
        """
        now = datetime.now(timezone.utc)
        query = db.query(AgentDecisionModel)

        # Status filter
        if status_filter:
            query = query.filter(AgentDecisionModel.review_status == status_filter)
        else:
            # Default to all active pending review states
            query = query.filter(AgentDecisionModel.review_status.in_(self.ACTIVE_PENDING_STATUSES))

        if asset_id:
            query = query.filter(AgentDecisionModel.asset_id == asset_id)

        # Batch retrieval of candidates
        decisions: List[AgentDecisionModel] = query.order_by(desc(AgentDecisionModel.created_at)).all()

        candidates: List[Tuple[Any, ...]] = []
        severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "MODERATE": 2, "LOW": 1}
        det_order = {"DETERIORATING": 3, "STABLE": 2, "IMPROVING": 1}
        rec_order = {"PERSISTENT": 3, "RECURRENT": 2, "NO_RECURRENCE": 1}

        for dec in decisions:
            metrics = dec.execution_metrics or {}
            hist_ctx = metrics.get("historical_context") or {}
            trends = metrics.get("inspection_trends") or {}
            inv_plan = metrics.get("investigation_plan") or {}

            # Authoritative fields
            risk_score = dec.risk_score
            severity = dec.risk_level or "LOW"
            op_action = dec.operational_decision
            rev_status = dec.review_status

            # Multi-phase intelligence
            det_status = trends.get("deterioration_status")
            rec_pattern = trends.get("recurrence_pattern")
            ev_suff = trends.get("evidence_sufficiency") or hist_ctx.get("evidence_sufficiency")
            inv_prio = inv_plan.get("priority")
            inv_plan_id = inv_plan.get("plan_id")
            diag_count = len(inv_plan.get("diagnostic_steps", []))
            gaps_count = len(inv_plan.get("information_gaps", []))
            source_ids = trends.get("source_inspection_ids", [])

            # Pending age
            pending_age: Optional[float] = None
            if dec.created_at:
                created_tz = dec.created_at if dec.created_at.tzinfo else dec.created_at.replace(tzinfo=timezone.utc)
                pending_age = max(0.0, (now - created_tz).total_seconds() / 3600.0)

            # Calculate deterministic score
            score, factors = self.calculate_priority_score(
                risk_score=risk_score,
                severity=severity,
                deterioration_status=det_status,
                recurrence_pattern=rec_pattern,
                evidence_sufficiency=ev_suff,
                investigation_priority=inv_prio,
                pending_age_hours=pending_age
            )
            p_class = self.classify_priority(score)

            if priority_class and p_class.upper() != priority_class.upper():
                continue

            rationale = self.build_rationale(
                priority_class=p_class,
                priority_score=score,
                risk_score=risk_score,
                severity=severity,
                deterioration_status=det_status,
                recurrence_pattern=rec_pattern
            )

            # Component resolution from evidence_reference
            comp_id = dec.evidence_reference.get("component_id") if isinstance(dec.evidence_reference, dict) else None
            if component_id and comp_id != component_id:
                continue

            # Deterministic sort tuple
            sev_rank = severity_order.get(severity.upper(), 0)
            det_rank = det_order.get((det_status or "").upper(), 0)
            rec_rank = rec_order.get((rec_pattern or "").upper(), 0)
            age_val = pending_age if pending_age is not None else 0.0

            sort_key = (
                -score,
                -risk_score,
                -sev_rank,
                -det_rank,
                -rec_rank,
                -age_val,
                dec.inspection_id
            )

            item_data = {
                "inspection_id": dec.inspection_id,
                "decision_id": dec.decision_id,
                "asset_id": dec.asset_id,
                "component_id": comp_id,
                "priority_class": p_class,
                "priority_score": score,
                "authoritative_risk_score": risk_score,
                "severity": severity,
                "operational_action": op_action,
                "review_status": rev_status,
                "human_review_required": dec.human_review_required,
                "investigation_priority": inv_prio,
                "deterioration_status": det_status,
                "recurrence_pattern": rec_pattern,
                "evidence_sufficiency": ev_suff,
                "investigation_plan_id": inv_plan_id,
                "diagnostic_steps_count": diag_count,
                "information_gaps_count": gaps_count,
                "pending_age_hours": round(pending_age, 2) if pending_age is not None else None,
                "rationale": rationale,
                "contributing_factors": factors,
                "source_inspection_ids": source_ids,
                "generated_by": "deterministic_prioritization_engine_v1",
                "authoritative": False
            }
            candidates.append((sort_key, item_data))

        # Deterministic sort
        candidates.sort(key=lambda c: c[0])

        # Slice limit and assign 1-indexed rank
        effective_limit = max(0, limit) if limit is not None else 50
        ranked_items: List[InspectionPriorityItem] = []
        for rank_idx, (_, data) in enumerate(candidates[:effective_limit], start=1):
            data["priority_rank"] = rank_idx
            ranked_items.append(InspectionPriorityItem(**data))

        return InspectionPriorityQueue(
            generated_at=now,
            total_pending=len(candidates),
            items=ranked_items,
            methodology_version=self.METHODOLOGY_VERSION,
            safety_notice="This queue recommends human review order only. It does not authorize or execute maintenance."
        )


inspection_prioritization_service = InspectionPrioritizationService()
