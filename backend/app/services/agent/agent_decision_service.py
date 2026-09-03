"""Service layer for persisting, querying, and reviewing Agent Inspection Decisions (Phase 3B/4)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models.agent_decision import (
    AgentDecisionModel,
    AgentReasoningTraceModel,
)
from backend.app.schemas.agent_decision import (
    AgentDecisionListResponse,
    AgentDecisionSummary,
    AgentInspectionDecision,
    TraceEvent,
    WorkOrderRecommendation,
)


class DecisionNotFoundError(Exception):
    """Exception raised when an agent decision is not found."""
    pass


class InvalidReviewActionError(Exception):
    """Exception raised when a review action is not supported."""
    pass


VALID_REVIEW_ACTIONS = {"APPROVED", "REJECTED", "REQUEST_FURTHER_INSPECTION"}


class AgentDecisionService:
    """Manages database persistence, queries, and review actions for autonomous agent decisions."""

    def save_decision(self, db: Session, decision: AgentInspectionDecision) -> AgentDecisionModel:
        """Persists an AgentInspectionDecision and all associated trace steps in PostgreSQL."""
        existing = db.query(AgentDecisionModel).filter(
            AgentDecisionModel.decision_id == decision.decision_id
        ).first()
        if existing:
            return existing

        db_decision = AgentDecisionModel(
            decision_id=decision.decision_id,
            inspection_id=decision.inspection_id,
            asset_id=decision.asset_id,
            operational_decision=decision.operational_decision,
            risk_score=decision.risk_assessment.get("risk_score", 0),
            risk_level=decision.risk_assessment.get("risk_level", "LOW"),
            decision_rationale=decision.decision_rationale,
            human_review_required=decision.human_review_required,
            review_status=decision.review_status,
            reviewer_name=decision.reviewer_name,
            review_action=decision.review_action,
            review_comment=decision.review_comment,
            reviewed_at=decision.reviewed_at,
            evidence_reference=decision.evidence_reference,
            risk_assessment=decision.risk_assessment,
            work_order=decision.work_order.model_dump(mode="json") if decision.work_order else None,
            warnings=decision.warnings,
            evidence_gaps=decision.evidence_gaps,
            execution_metrics={
                **decision.execution_metrics,
                **({"historical_context": decision.historical_context} if decision.historical_context else {}),
                **({"inspection_trends": decision.inspection_trends} if decision.inspection_trends else {}),
                **({"investigation_plan": decision.investigation_plan} if decision.investigation_plan else {})
            },
            created_at=decision.generated_at
        )
        db.add(db_decision)
        db.flush()

        # Add trace steps
        for step in decision.reasoning_trace:
            db_trace = AgentReasoningTraceModel(
                trace_id=f"trace-{decision.decision_id}-step-{step.step}",
                decision_id=decision.decision_id,
                step=step.step,
                stage=step.stage,
                tool=step.tool,
                input_summary=step.input_summary,
                result_summary=step.result_summary,
                decision_impact=step.decision_impact,
                status=step.status,
                duration_ms=step.duration_ms,
                created_at=step.timestamp
            )
            db.add(db_trace)

        db.commit()
        db.refresh(db_decision)
        return db_decision

    def get_decision(self, db: Session, decision_id: str) -> AgentInspectionDecision:
        """Retrieves a persisted agent decision by decision_id."""
        record = (
            db.query(AgentDecisionModel)
            .options(joinedload(AgentDecisionModel.traces))
            .filter(AgentDecisionModel.decision_id == decision_id)
            .first()
        )
        if not record:
            raise DecisionNotFoundError(f"Agent decision '{decision_id}' was not found.")

        traces = [
            TraceEvent(
                step=t.step,
                stage=t.stage,
                tool=t.tool,
                input_summary=t.input_summary,
                result_summary=t.result_summary,
                decision_impact=t.decision_impact,
                status=t.status,
                duration_ms=t.duration_ms,
                timestamp=t.created_at
            )
            for t in sorted(record.traces, key=lambda x: x.step)
        ]

        work_order_obj = None
        if record.work_order:
            work_order_obj = WorkOrderRecommendation.model_validate(record.work_order)

        return AgentInspectionDecision(
            schema_version="1.0",
            decision_id=record.decision_id,
            inspection_id=record.inspection_id,
            asset_id=record.asset_id,
            evidence_reference=record.evidence_reference,
            risk_assessment=record.risk_assessment,
            operational_decision=record.operational_decision,
            decision_rationale=record.decision_rationale,
            work_order=work_order_obj,
            reasoning_trace=traces,
            evidence_gaps=record.evidence_gaps or [],
            warnings=record.warnings or [],
            human_review_required=record.human_review_required,
            review_status=record.review_status,
            reviewer_name=record.reviewer_name,
            review_action=record.review_action,
            review_comment=record.review_comment,
            reviewed_at=record.reviewed_at,
            generated_at=record.created_at,
            execution_metrics=record.execution_metrics or {}
        )

    def get_decision_traces(self, db: Session, decision_id: str) -> List[TraceEvent]:
        """Retrieves the chronological reasoning trace for a decision."""
        decision = self.get_decision(db, decision_id)
        return decision.reasoning_trace

    def list_decisions(
        self,
        db: Session,
        risk_level: Optional[str] = None,
        operational_decision: Optional[str] = None,
        review_status: Optional[str] = None,
        asset_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> AgentDecisionListResponse:
        """Retrieves paginated and filtered inspection decision summaries."""
        query = db.query(AgentDecisionModel)

        if risk_level:
            query = query.filter(AgentDecisionModel.risk_level == risk_level.upper())
        if operational_decision:
            query = query.filter(AgentDecisionModel.operational_decision == operational_decision.upper())
        if review_status:
            query = query.filter(AgentDecisionModel.review_status == review_status.upper())
        if asset_id:
            query = query.filter(AgentDecisionModel.asset_id == asset_id)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    AgentDecisionModel.decision_id.ilike(search_pattern),
                    AgentDecisionModel.inspection_id.ilike(search_pattern),
                    AgentDecisionModel.asset_id.ilike(search_pattern)
                )
            )

        total = query.count()
        records = query.order_by(desc(AgentDecisionModel.created_at)).offset(offset).limit(limit).all()

        summaries = [
            AgentDecisionSummary(
                decision_id=r.decision_id,
                inspection_id=r.inspection_id,
                asset_id=r.asset_id,
                operational_decision=r.operational_decision,
                risk_score=r.risk_score,
                risk_level=r.risk_level,
                review_status=r.review_status,
                defect_count=r.evidence_reference.get("detections_count", 0) if r.evidence_reference else 0,
                created_at=r.created_at,
                reviewed_at=r.reviewed_at
            )
            for r in records
        ]

        return AgentDecisionListResponse(total=total, items=summaries)

    def apply_review(
        self,
        db: Session,
        decision_id: str,
        reviewer_name: str,
        review_action: str,
        review_comment: Optional[str] = None
    ) -> AgentInspectionDecision:
        """Applies human inspector review authorization to an existing decision."""
        action_upper = review_action.upper().strip()
        if action_upper not in VALID_REVIEW_ACTIONS:
            raise InvalidReviewActionError(
                f"Invalid review action '{review_action}'. Must be one of: {', '.join(VALID_REVIEW_ACTIONS)}"
            )

        record = db.query(AgentDecisionModel).filter(AgentDecisionModel.decision_id == decision_id).first()
        if not record:
            raise DecisionNotFoundError(f"Agent decision '{decision_id}' was not found.")

        # Update review fields
        record.review_status = action_upper
        record.reviewer_name = reviewer_name.strip()
        record.review_action = action_upper
        record.review_comment = review_comment.strip() if review_comment else None
        record.reviewed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(record)

        return self.get_decision(db, decision_id)

    def get_overview_kpis(self, db: Session) -> Dict[str, Any]:
        """Calculates real-time fleet overview KPIs from PostgreSQL."""
        total = db.query(func.count(AgentDecisionModel.id)).scalar() or 0
        pending = db.query(func.count(AgentDecisionModel.id)).filter(
            AgentDecisionModel.review_status == "PENDING_HUMAN_REVIEW"
        ).scalar() or 0
        critical = db.query(func.count(AgentDecisionModel.id)).filter(
            AgentDecisionModel.risk_level == "CRITICAL"
        ).scalar() or 0
        high = db.query(func.count(AgentDecisionModel.id)).filter(
            AgentDecisionModel.risk_level == "HIGH"
        ).scalar() or 0
        approved = db.query(func.count(AgentDecisionModel.id)).filter(
            AgentDecisionModel.review_status == "APPROVED"
        ).scalar() or 0
        rejected = db.query(func.count(AgentDecisionModel.id)).filter(
            AgentDecisionModel.review_status == "REJECTED"
        ).scalar() or 0

        return {
            "total_inspections": total,
            "pending_reviews": pending,
            "critical_findings": critical,
            "high_risk_findings": high,
            "approved_count": approved,
            "rejected_count": rejected,
        }


# Global service instance
agent_decision_service = AgentDecisionService()
