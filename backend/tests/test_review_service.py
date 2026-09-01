"""Unit tests for ReviewService state machine, work-order edits, and audit trail (Phase 2D)."""

import pytest
from backend.app.database.models.review import InspectionReview, ReviewAuditLog
from backend.app.database.session import SessionLocal
from backend.app.schemas.agent_assessment import (
    AgentInspectionAssessment,
    AgentReasoningTrace,
    DraftWorkOrder,
    InspectionAssessmentResponse,
)
from backend.app.schemas.review import (
    AuditEventType,
    ReviewActionRequest,
    ReviewCreateRequest,
    ReviewStatus,
    ReviewUpdateRequest,
    WorkOrderEditPayload,
)
from backend.app.services.review.review_service import (
    InvalidStateTransitionError,
    ReviewNotFoundError,
    review_service,
)


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_review():
    session = SessionLocal()
    # Clean up before module tests
    session.query(ReviewAuditLog).filter(ReviewAuditLog.review_id == "rev-insp-service-test-01-PIPE-SEG-4021").delete()
    session.query(InspectionReview).filter(InspectionReview.review_id == "rev-insp-service-test-01-PIPE-SEG-4021").delete()
    session.commit()
    yield
    # Clean up after module tests
    session.query(ReviewAuditLog).filter(ReviewAuditLog.review_id == "rev-insp-service-test-01-PIPE-SEG-4021").delete()
    session.query(InspectionReview).filter(InspectionReview.review_id == "rev-insp-service-test-01-PIPE-SEG-4021").delete()
    session.commit()
    session.close()


@pytest.fixture(scope="module")
def mock_assessment_response() -> InspectionAssessmentResponse:
    assessment = AgentInspectionAssessment(
        schema_version="1.0",
        assessment_id="assess-service-test-01",
        component_id="PIPE-SEG-4021",
        inspection_reference="insp-service-test-01",
        summary="Service test assessment summary",
        detected_defects=[{"detection_id": "det-001", "defect_type": "crack", "confidence": 0.85}],
        historical_context_summary="Historical context summary",
        reasoning="Engineering reasoning",
        risk_factors=["Fatigue"],
        recommended_actions=["Ultrasonic survey"],
        confidence="HIGH",
        uncertainty="Visual data only",
        human_review_required=True,
        source_references={"source_image_filename": "11112.jpg", "is_synthetic_data": True}
    )
    draft_wo = DraftWorkOrder(
        schema_version="1.0",
        draft_id="dwo-service-test-01",
        component_id="PIPE-SEG-4021",
        inspection_reference="insp-service-test-01",
        priority="HIGH",
        recommended_action="Execute ultrasonic inspection",
        justification="Observed crack",
        required_inspection="Ultrasonic NDE",
        suggested_team="Pipeline Integrity Team",
        estimated_downtime_hours=4.0,
        estimated_cost=2000.0,
        uncertainty="Visual data uncertainty",
        approval_status="PENDING_HUMAN_REVIEW"
    )
    trace = AgentReasoningTrace(
        trace_id="trace-service-test-01",
        component_id="PIPE-SEG-4021",
        input_evidence_references={"inspection_id": "insp-service-test-01"},
        historical_context_references={"asset_id": "ASSET-PL-01"},
        deterministic_decision_reference={"priority": "HIGH"},
        provider="ollama",
        model="gemma3:latest",
        output_reference="assess-service-test-01"
    )
    return InspectionAssessmentResponse(
        assessment=assessment,
        draft_work_order=draft_wo,
        reasoning_trace=trace
    )


def test_create_review_initializes_pending_status(db_session, mock_assessment_response):
    req = ReviewCreateRequest(assessment_response=mock_assessment_response)
    review = review_service.create_review(db_session, req)
    
    assert review.review_id == "rev-insp-service-test-01-PIPE-SEG-4021"
    assert review.status == ReviewStatus.PENDING_HUMAN_REVIEW.value
    assert review.component_id == "PIPE-SEG-4021"
    assert len(review.audit_logs) >= 1
    assert review.audit_logs[0].event_type == AuditEventType.REVIEW_CREATED.value


def test_list_reviews_and_filtering(db_session):
    summaries = review_service.list_reviews(db_session, limit=10)
    assert len(summaries) >= 2
    
    pending_summaries = review_service.list_reviews(db_session, status=ReviewStatus.PENDING_HUMAN_REVIEW)
    assert all(s.status == ReviewStatus.PENDING_HUMAN_REVIEW for s in pending_summaries)


def test_update_review_work_order_edits(db_session):
    review_id = "rev-insp-service-test-01-PIPE-SEG-4021"
    edit_payload = WorkOrderEditPayload(
        recommended_action="Updated action: immediate ultrasonic scan and magnetic particle testing.",
        estimated_cost=3500.0,
        estimated_downtime_hours=6.0
    )
    update_req = ReviewUpdateRequest(
        reviewer_id="INSP-7801",
        reviewer_name="S. Ray",
        reviewer_comments="Adjusted downtime estimate to 6 hours.",
        edited_work_order=edit_payload,
        status=ReviewStatus.IN_REVIEW
    )
    updated = review_service.update_review(db_session, review_id, update_req)
    
    assert updated.status == ReviewStatus.IN_REVIEW.value
    assert updated.reviewer_id == "INSP-7801"
    assert updated.edited_work_order["estimated_cost"] == 3500.0
    assert updated.edited_work_order["estimated_downtime_hours"] == 6.0
    assert any(log.event_type == AuditEventType.WORK_ORDER_EDITED.value for log in updated.audit_logs)


def test_approve_review_transition(db_session):
    review_id = "rev-insp-service-test-01-PIPE-SEG-4021"
    action = ReviewActionRequest(
        reviewer_id="INSP-7801",
        reviewer_name="S. Ray",
        comments="Approved following technical verification of wall thickness.",
    )
    approved = review_service.approve_review(db_session, review_id, action)
    
    assert approved.status == ReviewStatus.APPROVED.value
    assert approved.reviewed_at is not None
    assert approved.reviewer_comments == "Approved following technical verification of wall thickness."
    assert any(log.event_type == AuditEventType.WORK_ORDER_APPROVED.value for log in approved.audit_logs)


def test_invalid_state_transition_from_approved_fails(db_session):
    review_id = "rev-insp-service-test-01-PIPE-SEG-4021"
    action = ReviewActionRequest(
        reviewer_id="INSP-7801",
        reviewer_name="S. Ray",
        comments="Attempting invalid rejection after approval.",
    )
    with pytest.raises(InvalidStateTransitionError):
        review_service.reject_review(db_session, review_id, action)


def test_get_nonexistent_review_raises_error(db_session):
    with pytest.raises(ReviewNotFoundError):
        review_service.get_review(db_session, "nonexistent-rev-999")
