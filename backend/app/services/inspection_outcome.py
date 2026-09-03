"""Human Review Outcome Memory Service (Phase 7A/7B)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.database.models.inspection_outcome import InspectionOutcomeModel
from backend.app.schemas.inspection_outcome import (
    AIPredictionSnapshot,
    ConfirmedOutcomeSnapshot,
    CorrectionType,
    InspectionOutcomeCreate,
    InspectionOutcomeListResponse,
    InspectionOutcomeResponse,
    ReviewOutcomeStatus,
    ReviewerCorrection,
)


class InspectionNotFoundError(Exception):
    """Raised when the referenced inspection decision record does not exist."""
    pass


class OutcomeNotFoundError(Exception):
    """Raised when an inspection outcome record is not found."""
    pass


class DuplicateOutcomeError(Exception):
    """Raised when an outcome has already been recorded for this inspection and reviewer."""
    pass


class InspectionOutcomeService:
    """
    Service managing structured human review outcomes and historical ground-truth persistence.
    Operates strictly as review capture and learning memory; does not authorize maintenance or control.
    """

    @staticmethod
    def _compute_risk_band(risk_score: int) -> str:
        """Determines standardized risk band from numeric score."""
        if risk_score >= 80:
            return "CRITICAL"
        if risk_score >= 60:
            return "HIGH"
        if risk_score >= 40:
            return "MEDIUM"
        return "LOW"

    def record_outcome(
        self,
        db: Session,
        inspection_id: str,
        payload: InspectionOutcomeCreate
    ) -> InspectionOutcomeResponse:
        """
        Captures an authorized human inspector review outcome and snapshots AI predictions.
        Updates decision lifecycle state and persists immutable outcome record.
        """
        # 1. Fetch referenced authoritative agent decision
        decision = (
            db.query(AgentDecisionModel)
            .filter(AgentDecisionModel.inspection_id == inspection_id)
            .first()
        )
        if not decision:
            raise InspectionNotFoundError(f"Inspection with ID '{inspection_id}' was not found in agent decisions.")

        # 2. Check for existing identical outcome to prevent duplicate double-recording
        existing = (
            db.query(InspectionOutcomeModel)
            .filter(
                InspectionOutcomeModel.inspection_id == inspection_id,
                InspectionOutcomeModel.reviewer_id == payload.reviewer_id.strip()
            )
            .first()
        )
        if existing:
            raise DuplicateOutcomeError(
                f"Review outcome for inspection '{inspection_id}' by reviewer '{payload.reviewer_id}' already exists."
            )

        now = datetime.now(timezone.utc)

        # 3. Snapshot AI prediction at time of review
        ev_ref = decision.evidence_reference or {}
        det_count = ev_ref.get("detections_count", 0)
        ai_defect_detected = (det_count > 0) or (decision.risk_score >= 40)

        # Primary defect type
        primary_defect = "CRACK"
        if isinstance(ev_ref.get("detections"), list) and len(ev_ref["detections"]) > 0:
            primary_defect = ev_ref["detections"][0].get("defect_type", "CRACK")
        elif not ai_defect_detected:
            primary_defect = "NONE"

        ai_band = self._compute_risk_band(decision.risk_score)

        ai_snapshot = AIPredictionSnapshot(
            ai_risk_score=decision.risk_score,
            ai_severity=decision.risk_level or "LOW",
            ai_action=decision.operational_decision,
            ai_risk_band=ai_band,
            ai_defect_detected=ai_defect_detected,
            ai_defect_type=primary_defect
        )

        # 4. Formulate confirmed outcome snapshot
        confirmed_snapshot = ConfirmedOutcomeSnapshot(
            confirmed_defect_present=payload.confirmed_defect_present,
            confirmed_severity=payload.confirmed_severity.strip().upper(),
            confirmed_defect_type=payload.confirmed_defect_type.strip().upper(),
            reviewer_correction=payload.reviewer_correction
        )

        # 5. Evaluate overall agreement
        defect_agreed = (payload.confirmed_defect_present == ai_snapshot.ai_defect_detected)
        severity_agreed = (payload.confirmed_severity.strip().upper() == ai_snapshot.ai_severity.strip().upper())
        is_agreement = (payload.review_status == ReviewOutcomeStatus.APPROVED and defect_agreed and severity_agreed)

        # 6. Build persistent outcome record
        outcome_id = f"out-{inspection_id}-{uuid.uuid4().hex[:8]}"
        component_id = ev_ref.get("component_id")

        outcome_record = InspectionOutcomeModel(
            outcome_id=outcome_id,
            inspection_id=inspection_id,
            asset_id=decision.asset_id,
            component_id=component_id,
            reviewer_id=payload.reviewer_id.strip(),
            review_status=payload.review_status.value,
            ai_prediction_snapshot=ai_snapshot.model_dump(),
            confirmed_outcome_snapshot=confirmed_snapshot.model_dump(),
            review_metadata={
                "reviewer_comment": payload.reviewer_comment,
                "confirmation_source": payload.confirmation_source.value,
                "evidence_quality": payload.evidence_quality.value,
                "is_agreement": is_agreement
            },
            reviewed_at=now,
            created_at=now
        )
        db.add(outcome_record)

        # 7. Update AgentDecisionModel review status to sync lifecycle state
        # Invariant: Does not alter authoritative risk_score or operational_decision
        decision.review_status = payload.review_status.value
        decision.reviewer_name = payload.reviewer_id.strip()
        decision.review_action = payload.review_status.value
        decision.review_comment = payload.reviewer_comment
        decision.reviewed_at = now

        db.commit()
        db.refresh(outcome_record)

        return self._to_response(outcome_record)

    def get_outcome(self, db: Session, inspection_id: str) -> InspectionOutcomeResponse:
        """Retrieves the latest human review outcome for an inspection."""
        record = (
            db.query(InspectionOutcomeModel)
            .filter(InspectionOutcomeModel.inspection_id == inspection_id)
            .order_by(desc(InspectionOutcomeModel.created_at))
            .first()
        )
        if not record:
            raise OutcomeNotFoundError(f"Review outcome for inspection '{inspection_id}' was not found.")
        return self._to_response(record)

    def list_outcomes(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None,
        review_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> InspectionOutcomeListResponse:
        """Retrieves a paginated list of recorded human review outcomes."""
        query = db.query(InspectionOutcomeModel)

        if asset_id:
            query = query.filter(InspectionOutcomeModel.asset_id == asset_id)
        if component_id:
            query = query.filter(InspectionOutcomeModel.component_id == component_id)
        if review_status:
            query = query.filter(InspectionOutcomeModel.review_status == review_status.upper().strip())

        total = query.count()
        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, offset)

        records = (
            query.order_by(desc(InspectionOutcomeModel.created_at))
            .offset(safe_offset)
            .limit(safe_limit)
            .all()
        )

        return InspectionOutcomeListResponse(
            total=total,
            items=[self._to_response(r) for r in records]
        )

    def _to_response(self, record: InspectionOutcomeModel) -> InspectionOutcomeResponse:
        """Converts an ORM record to a validated Pydantic response."""
        meta = record.review_metadata or {}
        ai_data = record.ai_prediction_snapshot or {}
        conf_data = record.confirmed_outcome_snapshot or {}

        # Parse reviewer correction if present
        corr_data = conf_data.get("reviewer_correction")
        correction_obj = ReviewerCorrection.model_validate(corr_data) if corr_data else None

        return InspectionOutcomeResponse(
            id=record.id,
            outcome_id=record.outcome_id,
            inspection_id=record.inspection_id,
            asset_id=record.asset_id,
            component_id=record.component_id,
            reviewer_id=record.reviewer_id,
            review_status=ReviewOutcomeStatus(record.review_status),
            ai_prediction=AIPredictionSnapshot.model_validate(ai_data),
            confirmed_outcome=ConfirmedOutcomeSnapshot(
                confirmed_defect_present=conf_data.get("confirmed_defect_present", True),
                confirmed_severity=conf_data.get("confirmed_severity", "LOW"),
                confirmed_defect_type=conf_data.get("confirmed_defect_type", "UNKNOWN"),
                reviewer_correction=correction_obj
            ),
            reviewer_comment=meta.get("reviewer_comment"),
            confirmation_source=meta.get("confirmation_source", "VISUAL_INSPECTION"),
            evidence_quality=meta.get("evidence_quality", "ADEQUATE"),
            reviewed_at=record.reviewed_at,
            created_at=record.created_at,
            is_agreement=meta.get("is_agreement", False)
        )


inspection_outcome_service = InspectionOutcomeService()
