"""Historical Inspection Intelligence and Inspection Memory Service (Phase 6A)."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.database.models.asset import Asset
from backend.app.database.models.component import Component
from backend.app.database.models.defect import DefectRecord
from backend.app.database.models.inspection import InspectionRecord
from backend.app.schemas.inspection_history import (
    HistoricalInspectionContext,
    HistoricalInspectionRecord,
    HistoricalSummary,
    RiskTrendLiteral,
)

logger = logging.getLogger(__name__)


class InspectionHistoryService:
    """Service providing longitudinal inspection memory, recurrence tracking, and risk trends."""

    @staticmethod
    def _get_asset_component_ids(db: Session, asset_id: str) -> List[str]:
        """Retrieves all component IDs belonging to an asset."""
        components = db.query(Component.component_id).filter(Component.asset_id == asset_id).all()
        return [c[0] for c in components]

    def get_asset_history(
        self,
        db: Session,
        asset_id: str,
        exclude_inspection_id: Optional[str] = None,
        limit: int = 20
    ) -> List[HistoricalInspectionRecord]:
        """Retrieves prior inspection records associated with the specified asset."""
        comp_ids = self._get_asset_component_ids(db, asset_id)
        if not comp_ids:
            return []

        query = db.query(InspectionRecord).filter(InspectionRecord.component_id.in_(comp_ids))
        if exclude_inspection_id:
            query = query.filter(InspectionRecord.inspection_id != exclude_inspection_id)

        inspections = query.order_by(desc(InspectionRecord.inspection_timestamp)).limit(limit).all()
        if not inspections:
            return []

        # Correlate with agent decisions to extract authoritative risk scores and actions
        insp_ids = [r.inspection_id for r in inspections]
        decisions = (
            db.query(AgentDecisionModel)
            .filter(AgentDecisionModel.inspection_id.in_(insp_ids))
            .all()
        )
        dec_map = {d.inspection_id: d for d in decisions}

        records: List[HistoricalInspectionRecord] = []
        for insp in inspections:
            dec = dec_map.get(insp.inspection_id)
            records.append(
                HistoricalInspectionRecord(
                    inspection_id=insp.inspection_id,
                    asset_id=asset_id,
                    component_id=insp.component_id,
                    inspection_timestamp=insp.inspection_timestamp,
                    defect_type=insp.defect_type,
                    severity=insp.severity,
                    risk_score=dec.risk_score if dec else None,
                    authoritative_action=dec.operational_decision if dec else None,
                    human_review_status=dec.review_status if dec else None,
                    source_record_id=str(insp.id),
                    similarity_reason=f"Prior inspection on asset '{asset_id}'"
                )
            )
        return records

    def get_component_history(
        self,
        db: Session,
        component_id: str,
        exclude_inspection_id: Optional[str] = None,
        limit: int = 10
    ) -> List[HistoricalInspectionRecord]:
        """Retrieves historical inspection events specifically recorded on the target component."""
        comp = db.query(Component).filter(Component.component_id == component_id).first()
        asset_id = comp.asset_id if comp else "UNKNOWN_ASSET"

        query = db.query(InspectionRecord).filter(InspectionRecord.component_id == component_id)
        if exclude_inspection_id:
            query = query.filter(InspectionRecord.inspection_id != exclude_inspection_id)

        inspections = query.order_by(desc(InspectionRecord.inspection_timestamp)).limit(limit).all()
        if not inspections:
            return []

        insp_ids = [r.inspection_id for r in inspections]
        decisions = (
            db.query(AgentDecisionModel)
            .filter(AgentDecisionModel.inspection_id.in_(insp_ids))
            .all()
        )
        dec_map = {d.inspection_id: d for d in decisions}

        records: List[HistoricalInspectionRecord] = []
        for insp in inspections:
            dec = dec_map.get(insp.inspection_id)
            records.append(
                HistoricalInspectionRecord(
                    inspection_id=insp.inspection_id,
                    asset_id=asset_id,
                    component_id=insp.component_id,
                    inspection_timestamp=insp.inspection_timestamp,
                    defect_type=insp.defect_type,
                    severity=insp.severity,
                    risk_score=dec.risk_score if dec else None,
                    authoritative_action=dec.operational_decision if dec else None,
                    human_review_status=dec.review_status if dec else None,
                    source_record_id=str(insp.id),
                    similarity_reason=f"Prior inspection on component '{component_id}'"
                )
            )
        return records

    def get_previous_decisions(
        self,
        db: Session,
        asset_id: str,
        exclude_decision_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieves authoritative previous agent decision records for the asset."""
        query = db.query(AgentDecisionModel).filter(AgentDecisionModel.asset_id == asset_id)
        if exclude_decision_id:
            query = query.filter(AgentDecisionModel.decision_id != exclude_decision_id)

        decisions = query.order_by(desc(AgentDecisionModel.created_at)).limit(limit).all()
        return [
            {
                "decision_id": d.decision_id,
                "inspection_id": d.inspection_id,
                "operational_decision": d.operational_decision,
                "risk_score": d.risk_score,
                "risk_level": d.risk_level,
                "review_status": d.review_status,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in decisions
        ]

    def get_similar_inspections(
        self,
        db: Session,
        defect_type: str,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None,
        exclude_inspection_id: Optional[str] = None,
        limit: int = 5
    ) -> List[HistoricalInspectionRecord]:
        """
        Deterministic multi-tier similarity matching based on component, asset, and defect classification.
        Guarantees exact source traceability and transparent similarity explanations.
        """
        similar_records: List[HistoricalInspectionRecord] = []
        seen_ids = set()
        if exclude_inspection_id:
            seen_ids.add(exclude_inspection_id)

        # Tier 1: Same component AND same defect type
        if component_id:
            t1_query = (
                db.query(InspectionRecord)
                .filter(InspectionRecord.component_id == component_id)
                .filter(InspectionRecord.defect_type.ilike(f"%{defect_type}%"))
            )
            for r in t1_query.order_by(desc(InspectionRecord.inspection_timestamp)).limit(limit).all():
                if r.inspection_id not in seen_ids:
                    seen_ids.add(r.inspection_id)
                    similar_records.append(
                        HistoricalInspectionRecord(
                            inspection_id=r.inspection_id,
                            asset_id=asset_id or "UNKNOWN",
                            component_id=r.component_id,
                            inspection_timestamp=r.inspection_timestamp,
                            defect_type=r.defect_type,
                            severity=r.severity,
                            source_record_id=str(r.id),
                            similarity_reason=f"Identical defect '{defect_type}' on same component '{component_id}'"
                        )
                    )

        # Tier 2: Same asset AND same defect type
        if len(similar_records) < limit and asset_id:
            comp_ids = self._get_asset_component_ids(db, asset_id)
            if comp_ids:
                t2_query = (
                    db.query(InspectionRecord)
                    .filter(InspectionRecord.component_id.in_(comp_ids))
                    .filter(InspectionRecord.defect_type.ilike(f"%{defect_type}%"))
                )
                for r in t2_query.order_by(desc(InspectionRecord.inspection_timestamp)).limit(limit - len(similar_records)).all():
                    if r.inspection_id not in seen_ids:
                        seen_ids.add(r.inspection_id)
                        similar_records.append(
                            HistoricalInspectionRecord(
                                inspection_id=r.inspection_id,
                                asset_id=asset_id,
                                component_id=r.component_id,
                                inspection_timestamp=r.inspection_timestamp,
                                defect_type=r.defect_type,
                                severity=r.severity,
                                source_record_id=str(r.id),
                                similarity_reason=f"Matching defect '{defect_type}' on same asset '{asset_id}'"
                            )
                        )

        # Tier 3: Fleet-wide matching defect type
        if len(similar_records) < limit:
            t3_query = (
                db.query(InspectionRecord)
                .filter(InspectionRecord.defect_type.ilike(f"%{defect_type}%"))
            )
            for r in t3_query.order_by(desc(InspectionRecord.inspection_timestamp)).limit(limit - len(similar_records)).all():
                if r.inspection_id not in seen_ids:
                    seen_ids.add(r.inspection_id)
                    similar_records.append(
                        HistoricalInspectionRecord(
                            inspection_id=r.inspection_id,
                            asset_id="FLEET",
                            component_id=r.component_id,
                            inspection_timestamp=r.inspection_timestamp,
                            defect_type=r.defect_type,
                            severity=r.severity,
                            source_record_id=str(r.id),
                            similarity_reason=f"Fleet-wide matching defect '{defect_type}' precedent"
                        )
                    )

        return similar_records[:limit]

    def calculate_risk_trend(self, risk_scores: List[int]) -> Tuple[RiskTrendLiteral, str]:
        """
        Computes a deterministic mathematical risk trend from a chronological list of risk scores.
        Expects risk_scores ordered from oldest to newest.
        Requires at least 2 valid historical scores to establish a trend.
        """
        if not risk_scores or len(risk_scores) < 2:
            return (
                "INSUFFICIENT_HISTORY",
                "Fewer than 2 valid historical risk assessments exist for trend analysis."
            )

        oldest = risk_scores[0]
        newest = risk_scores[-1]
        delta = newest - oldest

        if delta >= 10:
            return (
                "INCREASING",
                f"Risk score increased by {delta} points (from {oldest} to {newest}) across {len(risk_scores)} assessments."
            )
        elif delta <= -10:
            return (
                "DECREASING",
                f"Risk score decreased by {abs(delta)} points (from {oldest} to {newest}) across {len(risk_scores)} assessments."
            )
        else:
            return (
                "STABLE",
                f"Risk scores remained stable within +/- 10 points (ranging {min(risk_scores)} to {max(risk_scores)})."
            )

    def build_historical_context(
        self,
        db: Optional[Session],
        asset_id: str,
        component_id: Optional[str] = None,
        defect_type: Optional[str] = None,
        current_inspection_id: Optional[str] = None
    ) -> HistoricalInspectionContext:
        """
        Orchestrates historical retrieval, deterministic recurrence detection, and risk trend calculation.
        Guarantees non-authoritative supporting context and safe fail-safe degradation.
        """
        if db is None:
            return HistoricalInspectionContext(
                has_history=False,
                asset_id=asset_id,
                component_id=component_id,
                summary=HistoricalSummary(
                    trend_explanation="Database session unavailable; historical memory offline."
                ),
                retrieval_metadata={"status": "DB_UNAVAILABLE"}
            )

        try:
            # 1. Retrieve asset inspection history
            asset_history = self.get_asset_history(
                db=db,
                asset_id=asset_id,
                exclude_inspection_id=current_inspection_id,
                limit=15
            )

            # 2. Retrieve component-specific history
            component_history: List[HistoricalInspectionRecord] = []
            if component_id:
                component_history = self.get_component_history(
                    db=db,
                    component_id=component_id,
                    exclude_inspection_id=current_inspection_id,
                    limit=10
                )

            # 3. Retrieve prior agent decisions
            prev_decisions = self.get_previous_decisions(
                db=db,
                asset_id=asset_id,
                limit=10
            )

            # 4. Retrieve similar inspections matching primary defect
            similar_inspections: List[HistoricalInspectionRecord] = []
            if defect_type:
                similar_inspections = self.get_similar_inspections(
                    db=db,
                    defect_type=defect_type,
                    asset_id=asset_id,
                    component_id=component_id,
                    exclude_inspection_id=current_inspection_id,
                    limit=5
                )

            # 5. Compute recurrence
            recurring_defect = False
            if defect_type:
                search_term = defect_type.lower()
                for rec in asset_history:
                    if rec.defect_type and search_term in rec.defect_type.lower():
                        recurring_defect = True
                        break

            # 6. Compute critical events
            critical_events = 0
            for d in prev_decisions:
                if d.get("risk_score", 0) >= 80 or d.get("operational_decision") == "URGENT_ENGINEERING_REVIEW":
                    critical_events += 1

            for h in asset_history:
                if h.severity and h.severity.upper() in ("CRITICAL", "HIGH"):
                    critical_events += 1

            # 7. Compute risk trend from chronological scores (oldest to newest)
            chronological_scores: List[int] = []
            # prev_decisions is ordered newest-first, so reverse to oldest-first
            for d in reversed(prev_decisions):
                score = d.get("risk_score")
                if score is not None:
                    chronological_scores.append(int(score))

            trend, explanation = self.calculate_risk_trend(chronological_scores)
            latest_risk = prev_decisions[0].get("risk_score") if prev_decisions else None

            summary = HistoricalSummary(
                total_previous_inspections=len(asset_history),
                same_component_inspections=len(component_history),
                previous_critical_events=critical_events,
                recurring_defect_detected=recurring_defect,
                latest_previous_risk_score=latest_risk,
                risk_trend=trend,
                trend_explanation=explanation
            )

            has_history = (len(asset_history) > 0 or len(prev_decisions) > 0)

            return HistoricalInspectionContext(
                has_history=has_history,
                asset_id=asset_id,
                component_id=component_id,
                summary=summary,
                recent_inspections=asset_history[:5],
                similar_inspections=similar_inspections,
                previous_decisions=prev_decisions[:5],
                retrieval_metadata={
                    "status": "SUCCESS",
                    "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                    "records_queried": len(asset_history) + len(similar_inspections),
                    "chronological_score_count": len(chronological_scores)
                }
            )

        except Exception as e:
            logger.warning(f"Historical context retrieval encountered an error: {e}")
            return HistoricalInspectionContext(
                has_history=False,
                asset_id=asset_id,
                component_id=component_id,
                summary=HistoricalSummary(
                    trend_explanation=f"Historical retrieval degraded safely due to database query error: {e}"
                ),
                retrieval_metadata={
                    "status": "ERROR",
                    "error_message": str(e)
                }
            )


inspection_history_service = InspectionHistoryService()
