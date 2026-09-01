"""Service layer managing Human-in-the-Loop review lifecycle, work order editing, and audit logging (Phase 2D)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models.review import InspectionReview, ReviewAuditLog
from backend.app.schemas.review import (
    AuditEventType,
    InspectionReviewSummary,
    ReviewActionRequest,
    ReviewCreateRequest,
    ReviewStatus,
    ReviewUpdateRequest,
    VALID_REVIEW_TRANSITIONS,
)


class InvalidStateTransitionError(Exception):
    """Exception raised when an invalid review status transition is attempted."""
    pass


class ReviewNotFoundError(Exception):
    """Exception raised when the requested review is not found."""
    pass


class ReviewService:
    """Business logic for inspector review workflow and audit preservation."""

    @staticmethod
    def _create_audit_entry(
        db: Session,
        review_id: str,
        event_type: AuditEventType,
        previous_status: Optional[str],
        new_status: Optional[str],
        reviewer_id: Optional[str] = None,
        reviewer_name: Optional[str] = None,
        change_summary: Optional[str] = None,
        metadata_snapshot: Optional[Dict[str, Any]] = None
    ) -> ReviewAuditLog:
        """Helper to create and persist an immutable audit record."""
        audit = ReviewAuditLog(
            audit_id=f"aud-{uuid.uuid4().hex[:12]}",
            review_id=review_id,
            event_type=event_type.value,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            previous_status=previous_status,
            new_status=new_status,
            change_summary=change_summary,
            metadata_snapshot=metadata_snapshot,
            created_at=datetime.now(timezone.utc)
        )
        db.add(audit)
        return audit

    def create_review(self, db: Session, request: ReviewCreateRequest) -> InspectionReview:
        """Creates a new persistent InspectionReview initialized in PENDING_HUMAN_REVIEW state."""
        resp = request.assessment_response
        assessment = resp.assessment
        dwo = resp.draft_work_order
        trace = resp.reasoning_trace

        review_id = f"rev-{assessment.inspection_reference}-{assessment.component_id}"
        
        # Check if already exists; if so, return existing
        existing = db.query(InspectionReview).filter(InspectionReview.review_id == review_id).first()
        if existing:
            return existing

        priority = request.priority or dwo.priority

        review = InspectionReview(
            review_id=review_id,
            inspection_id=assessment.inspection_reference,
            component_id=assessment.component_id,
            assessment_id=assessment.assessment_id,
            status=ReviewStatus.PENDING_HUMAN_REVIEW.value,
            priority=priority,
            reviewer_id=None,
            reviewer_name=None,
            reviewer_comments=None,
            original_vision_evidence=trace.input_evidence_references,
            original_decision=trace.deterministic_decision_reference,
            original_assessment=assessment.model_dump(mode="json"),
            original_draft_work_order=dwo.model_dump(mode="json"),
            reasoning_trace=trace.model_dump(mode="json"),
            edited_work_order=None,
            reviewed_at=None,
        )
        db.add(review)
        db.flush()

        # Create initial audit log
        self._create_audit_entry(
            db=db,
            review_id=review_id,
            event_type=AuditEventType.REVIEW_CREATED,
            previous_status=None,
            new_status=ReviewStatus.PENDING_HUMAN_REVIEW.value,
            change_summary="Inspection assessment received and initialized for human review."
        )

        db.commit()
        db.refresh(review)
        return review

    def get_review(self, db: Session, review_id: str) -> InspectionReview:
        """Retrieves a single review with its complete audit history."""
        review = (
            db.query(InspectionReview)
            .options(joinedload(InspectionReview.audit_logs))
            .filter(InspectionReview.review_id == review_id)
            .first()
        )
        if not review:
            raise ReviewNotFoundError(f"Review '{review_id}' was not found.")
        return review

    def list_reviews(
        self,
        db: Session,
        status: Optional[ReviewStatus] = None,
        priority: Optional[str] = None,
        component_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InspectionReviewSummary]:
        """Lists reviews formatted for inspector queue dashboard."""
        query = db.query(InspectionReview)

        if status:
            query = query.filter(InspectionReview.status == status.value)
        if priority:
            query = query.filter(InspectionReview.priority == priority.upper())
        if component_id:
            query = query.filter(InspectionReview.component_id == component_id)

        reviews = (
            query.order_by(desc(InspectionReview.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

        summaries = []
        for r in reviews:
            # Extract summary metrics from original_assessment
            assess = r.original_assessment or {}
            defects = assess.get("detected_defects", [])
            max_conf = max([d.get("confidence", 0.0) for d in defects], default=0.0)
            
            src_refs = assess.get("source_references", {})
            src_img = src_refs.get("source_image_filename", "inspection_image.jpg")
            
            # Evidence quality flags
            ev_refs = r.original_vision_evidence or {}
            blur_score = ev_refs.get("blur_score", 100.0)
            warnings = ev_refs.get("warnings", [])

            summaries.append(
                InspectionReviewSummary(
                    review_id=r.review_id,
                    inspection_id=r.inspection_id,
                    component_id=r.component_id,
                    assessment_id=r.assessment_id,
                    status=ReviewStatus(r.status),
                    priority=r.priority,
                    detection_count=len(defects),
                    max_confidence=round(max_conf, 3),
                    quality_blur_score=round(blur_score, 1),
                    quality_warnings=warnings if isinstance(warnings, list) else [],
                    source_image_filename=src_img,
                    reviewer_name=r.reviewer_name,
                    created_at=r.created_at,
                    reviewed_at=r.reviewed_at,
                )
            )
        return summaries

    def update_review(self, db: Session, review_id: str, payload: ReviewUpdateRequest) -> InspectionReview:
        """Updates reviewer notes, work order edits, or transitions to IN_REVIEW."""
        review = self.get_review(db, review_id)
        current_status = ReviewStatus(review.status)

        # Validate status change if requested
        if payload.status and payload.status != current_status:
            allowed = VALID_REVIEW_TRANSITIONS.get(current_status, set())
            if payload.status not in allowed:
                raise InvalidStateTransitionError(
                    f"Cannot transition review '{review_id}' from '{current_status.value}' to '{payload.status.value}'."
                )
            review.status = payload.status.value
            self._create_audit_entry(
                db=db,
                review_id=review_id,
                event_type=AuditEventType.REVIEW_OPENED if payload.status == ReviewStatus.IN_REVIEW else AuditEventType.WORK_ORDER_EDITED,
                previous_status=current_status.value,
                new_status=payload.status.value,
                reviewer_id=payload.reviewer_id or review.reviewer_id,
                reviewer_name=payload.reviewer_name or review.reviewer_name,
                change_summary=f"Review status transitioned to {payload.status.value}"
            )

        if payload.reviewer_id:
            review.reviewer_id = payload.reviewer_id
        if payload.reviewer_name:
            review.reviewer_name = payload.reviewer_name
        if payload.reviewer_comments:
            review.reviewer_comments = payload.reviewer_comments

        # Handle work order edits
        if payload.edited_work_order:
            existing_edits = review.edited_work_order or dict(review.original_draft_work_order)
            update_dict = payload.edited_work_order.model_dump(exclude_unset=True)
            existing_edits.update(update_dict)
            review.edited_work_order = existing_edits

            self._create_audit_entry(
                db=db,
                review_id=review_id,
                event_type=AuditEventType.WORK_ORDER_EDITED,
                previous_status=review.status,
                new_status=review.status,
                reviewer_id=payload.reviewer_id or review.reviewer_id,
                reviewer_name=payload.reviewer_name or review.reviewer_name,
                change_summary=f"Draft work order edited: {list(update_dict.keys())}",
                metadata_snapshot={"edited_fields": list(update_dict.keys())}
            )

        db.commit()
        db.refresh(review)
        return review

    def approve_review(self, db: Session, review_id: str, action: ReviewActionRequest) -> InspectionReview:
        """Explicitly approves the draft work order with mandatory reviewer attribution."""
        review = self.get_review(db, review_id)
        current_status = ReviewStatus(review.status)

        allowed = VALID_REVIEW_TRANSITIONS.get(current_status, set())
        if ReviewStatus.APPROVED not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot approve review '{review_id}' in state '{current_status.value}'."
            )

        # Apply any pending work order edits
        if action.edited_work_order:
            existing_edits = review.edited_work_order or dict(review.original_draft_work_order)
            existing_edits.update(action.edited_work_order.model_dump(exclude_unset=True))
            existing_edits["approval_status"] = "APPROVED"
            review.edited_work_order = existing_edits
        elif review.edited_work_order:
            review.edited_work_order["approval_status"] = "APPROVED"

        old_status = review.status
        review.status = ReviewStatus.APPROVED.value
        review.reviewer_id = action.reviewer_id
        review.reviewer_name = action.reviewer_name
        review.reviewer_comments = action.comments
        review.reviewed_at = datetime.now(timezone.utc)

        self._create_audit_entry(
            db=db,
            review_id=review_id,
            event_type=AuditEventType.WORK_ORDER_APPROVED,
            previous_status=old_status,
            new_status=ReviewStatus.APPROVED.value,
            reviewer_id=action.reviewer_id,
            reviewer_name=action.reviewer_name,
            change_summary=f"Inspector Approved: {action.comments}"
        )

        db.commit()
        db.refresh(review)
        return review

    def reject_review(self, db: Session, review_id: str, action: ReviewActionRequest) -> InspectionReview:
        """Explicitly rejects the draft work order with mandatory reviewer justification."""
        review = self.get_review(db, review_id)
        current_status = ReviewStatus(review.status)

        allowed = VALID_REVIEW_TRANSITIONS.get(current_status, set())
        if ReviewStatus.REJECTED not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot reject review '{review_id}' in state '{current_status.value}'."
            )

        old_status = review.status
        review.status = ReviewStatus.REJECTED.value
        review.reviewer_id = action.reviewer_id
        review.reviewer_name = action.reviewer_name
        review.reviewer_comments = action.comments
        review.reviewed_at = datetime.now(timezone.utc)

        if review.edited_work_order:
            review.edited_work_order["approval_status"] = "REJECTED"

        self._create_audit_entry(
            db=db,
            review_id=review_id,
            event_type=AuditEventType.WORK_ORDER_REJECTED,
            previous_status=old_status,
            new_status=ReviewStatus.REJECTED.value,
            reviewer_id=action.reviewer_id,
            reviewer_name=action.reviewer_name,
            change_summary=f"Inspector Rejected: {action.comments}"
        )

        db.commit()
        db.refresh(review)
        return review

    def request_revision(self, db: Session, review_id: str, action: ReviewActionRequest) -> InspectionReview:
        """Requests inspection revision or supplementary NDT before decision."""
        review = self.get_review(db, review_id)
        current_status = ReviewStatus(review.status)

        allowed = VALID_REVIEW_TRANSITIONS.get(current_status, set())
        if ReviewStatus.REVISION_REQUESTED not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot request revision for review '{review_id}' in state '{current_status.value}'."
            )

        old_status = review.status
        review.status = ReviewStatus.REVISION_REQUESTED.value
        review.reviewer_id = action.reviewer_id
        review.reviewer_name = action.reviewer_name
        review.reviewer_comments = action.comments
        review.reviewed_at = datetime.now(timezone.utc)

        self._create_audit_entry(
            db=db,
            review_id=review_id,
            event_type=AuditEventType.REVISION_REQUESTED,
            previous_status=old_status,
            new_status=ReviewStatus.REVISION_REQUESTED.value,
            reviewer_id=action.reviewer_id,
            reviewer_name=action.reviewer_name,
            change_summary=f"Inspector Requested Revision: {action.comments}"
        )

        db.commit()
        db.refresh(review)
        return review

    def get_audit_trail(self, db: Session, review_id: str) -> List[ReviewAuditLog]:
        """Retrieves the chronological audit history for a given review."""
        review = self.get_review(db, review_id)
        return review.audit_logs


# Global service instance
review_service = ReviewService()
