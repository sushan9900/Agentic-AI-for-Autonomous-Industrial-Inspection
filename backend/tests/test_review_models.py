"""Unit tests for InspectionReview and ReviewAuditLog PostgreSQL ORM models (Phase 2D)."""

import pytest
from backend.app.database.models.review import InspectionReview, ReviewAuditLog
from backend.app.database.session import SessionLocal


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_inspection_review_query_and_relationships(db_session):
    review = db_session.query(InspectionReview).filter(InspectionReview.review_id == "rev-insp-11112-44e62c64-PIPE-SEG-4021").first()
    assert review is not None
    assert review.component_id == "PIPE-SEG-4021"
    assert review.status in ("PENDING_HUMAN_REVIEW", "IN_REVIEW", "APPROVED", "REJECTED", "REVISION_REQUESTED")
    assert review.priority == "CRITICAL"
    assert review.component is not None
    assert review.component.name == "Primary Body Segment 4021 (Span 40m - 52m)"
    assert len(review.audit_logs) >= 1


def test_review_audit_log_relationship(db_session):
    audit = db_session.query(ReviewAuditLog).filter(ReviewAuditLog.audit_id == "aud-init-001").first()
    assert audit is not None
    assert audit.review_id == "rev-insp-11112-44e62c64-PIPE-SEG-4021"
    assert audit.event_type == "REVIEW_CREATED"
    assert audit.new_status == "PENDING_HUMAN_REVIEW"
    assert audit.review is not None
    assert audit.review.component_id == "PIPE-SEG-4021"
