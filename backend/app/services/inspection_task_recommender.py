"""Inspection Task Recommendation Engine (Phase 8C)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.schemas.inspection_task import TimingWindow
from backend.app.schemas.task_recommendation import (
    RecommendationType,
    RecommendationUrgency,
    TaskRecommendation,
    TaskRecommendationsResponse,
)
from backend.app.services.adaptive_recommendation import adaptive_recommendation_service
from backend.app.services.inspection_timing import inspection_timing_service


class InspectionTaskRecommender:
    """
    Synthesizes multi-phase inspection intelligence into explainable task recommendations.
    Deterministic advisory execution; authoritative = False, human_approval_required = True.
    """

    def generate_recommendations(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None,
        limit: int = 50
    ) -> List[TaskRecommendation]:
        """
        Generates actionable, non-authoritative inspection task recommendations.
        """
        query = db.query(AgentDecisionModel)
        if asset_id:
            query = query.filter(AgentDecisionModel.asset_id == asset_id)

        decisions = query.order_by(desc(AgentDecisionModel.created_at)).limit(limit).all()
        adaptive_recs = adaptive_recommendation_service.generate_recommendations(db=db, asset_id=asset_id)

        recommendations: List[TaskRecommendation] = []
        now = datetime.now(timezone.utc)

        for dec in decisions:
            ev_ref = dec.evidence_reference or {}
            metrics = dec.execution_metrics or {}
            trends = metrics.get("inspection_trends") or {}
            inv_plan = metrics.get("investigation_plan") or {}
            comp_id = ev_ref.get("component_id") or dec.asset_id

            if component_id and comp_id != component_id:
                continue

            det_status = trends.get("deterioration_status", "UNKNOWN")
            rec_pattern = trends.get("recurrence_pattern", "UNKNOWN")
            ev_suff = trends.get("evidence_sufficiency", "SUFFICIENT")
            gaps = inv_plan.get("unobserved_gaps", [])

            # Compute timing window
            timing = inspection_timing_service.evaluate_timing(
                risk_score=dec.risk_score,
                severity=dec.risk_level or "LOW",
                deterioration_status=det_status,
                recurrence_pattern=rec_pattern
            )

            rec_urgency = (
                RecommendationUrgency.CRITICAL if dec.risk_score >= 80
                else RecommendationUrgency.HIGH if dec.risk_score >= 60
                else RecommendationUrgency.MEDIUM if dec.risk_score >= 40
                else RecommendationUrgency.LOW
            )

            # Rule A: Evidence insufficiency or missing gaps -> REQUEST_ADDITIONAL_EVIDENCE
            if ev_suff == "INSUFFICIENT" or len(gaps) > 0:
                rec_id = f"rec-ev-{dec.inspection_id}-{uuid.uuid4().hex[:6]}"
                recommendations.append(
                    TaskRecommendation(
                        recommendation_id=rec_id,
                        asset_id=dec.asset_id,
                        component_id=comp_id,
                        inspection_id=dec.inspection_id,
                        recommendation_type=RecommendationType.REQUEST_ADDITIONAL_EVIDENCE,
                        urgency=rec_urgency,
                        timing_window=timing.timing_window,
                        reason=(
                            f"Inspection '{dec.inspection_id}' on component '{comp_id}' exhibits evidence gaps "
                            f"or insufficient visual resolution. Additional targeted imagery recommended."
                        ),
                        supporting_evidence_ids=gaps[:3],
                        supporting_inspection_ids=[dec.inspection_id],
                        authoritative=False,
                        human_approval_required=True,
                        created_at=now
                    )
                )

            # Rule B: High risk / Deteriorating defect -> REPEAT_INSPECTION
            elif det_status == "DETERIORATING" and dec.risk_score >= 70:
                rec_id = f"rec-rpt-{dec.inspection_id}-{uuid.uuid4().hex[:6]}"
                recommendations.append(
                    TaskRecommendation(
                        recommendation_id=rec_id,
                        asset_id=dec.asset_id,
                        component_id=comp_id,
                        inspection_id=dec.inspection_id,
                        recommendation_type=RecommendationType.REPEAT_INSPECTION,
                        urgency=RecommendationUrgency.CRITICAL if dec.risk_score >= 80 else RecommendationUrgency.HIGH,
                        timing_window=timing.timing_window,
                        reason=(
                            f"Component '{comp_id}' shows active deterioration ({det_status}) with risk score "
                            f"{dec.risk_score}/100. Follow-up verification inspection recommended."
                        ),
                        supporting_evidence_ids=[],
                        supporting_inspection_ids=[dec.inspection_id],
                        authoritative=False,
                        human_approval_required=True,
                        created_at=now
                    )
                )

            # Rule C: Pending human review -> REVIEW_EXISTING_INSPECTION
            elif dec.review_status in ("PENDING_HUMAN_REVIEW", "IN_REVIEW"):
                rec_id = f"rec-rev-{dec.inspection_id}-{uuid.uuid4().hex[:6]}"
                recommendations.append(
                    TaskRecommendation(
                        recommendation_id=rec_id,
                        asset_id=dec.asset_id,
                        component_id=comp_id,
                        inspection_id=dec.inspection_id,
                        recommendation_type=RecommendationType.REVIEW_EXISTING_INSPECTION,
                        urgency=rec_urgency,
                        timing_window=timing.timing_window,
                        reason=(
                            f"Pending inspection '{dec.inspection_id}' has derived review priority ({rec_urgency.value}) "
                            f"and requires human engineering validation."
                        ),
                        supporting_evidence_ids=[],
                        supporting_inspection_ids=[dec.inspection_id],
                        authoritative=False,
                        human_approval_required=True,
                        created_at=now
                    )
                )

        return recommendations

    def get_recommendations_response(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None
    ) -> TaskRecommendationsResponse:
        """Packages active recommendations in standard envelope."""
        recs = self.generate_recommendations(db, asset_id, component_id)
        return TaskRecommendationsResponse(
            total_recommendations=len(recs),
            recommendations=recs
        )


inspection_task_recommender = InspectionTaskRecommender()
