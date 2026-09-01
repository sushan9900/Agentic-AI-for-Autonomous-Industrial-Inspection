"""API tests for /api/v1/reviews and /api/v1/images (Phase 2D)."""

import pytest
from fastapi.testclient import TestClient
from backend.app.database.models.review import InspectionReview, ReviewAuditLog
from backend.app.database.session import SessionLocal
from backend.app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def reset_seed_review_state():
    session = SessionLocal()
    # Reset review to initial seeded state before tests
    review = session.query(InspectionReview).filter(
        InspectionReview.review_id == "rev-insp-11112-44e62c64-PIPE-SEG-4021"
    ).first()
    if review:
        review.status = "PENDING_HUMAN_REVIEW"
        review.edited_work_order = None
        review.reviewed_at = None
        review.reviewer_id = None
        review.reviewer_name = None
        review.reviewer_comments = None
        session.query(ReviewAuditLog).filter(
            ReviewAuditLog.review_id == "rev-insp-11112-44e62c64-PIPE-SEG-4021",
            ReviewAuditLog.audit_id != "aud-init-001"
        ).delete()
        session.commit()
    yield
    # Reset review after tests to keep database clean
    review = session.query(InspectionReview).filter(
        InspectionReview.review_id == "rev-insp-11112-44e62c64-PIPE-SEG-4021"
    ).first()
    if review:
        review.status = "PENDING_HUMAN_REVIEW"
        review.edited_work_order = None
        review.reviewed_at = None
        review.reviewer_id = None
        review.reviewer_name = None
        review.reviewer_comments = None
        session.query(ReviewAuditLog).filter(
            ReviewAuditLog.review_id == "rev-insp-11112-44e62c64-PIPE-SEG-4021",
            ReviewAuditLog.audit_id != "aud-init-001"
        ).delete()
        session.commit()
    session.close()


def test_list_reviews_api():
    response = client.get("/api/v1/reviews")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "review_id" in data[0]
    assert "status" in data[0]


def test_get_review_detail_api():
    review_id = "rev-insp-11112-44e62c64-PIPE-SEG-4021"
    response = client.get(f"/api/v1/reviews/{review_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == review_id
    assert "original_assessment" in data
    assert "original_draft_work_order" in data
    assert "audit_logs" in data


def test_update_review_work_order_api():
    review_id = "rev-insp-11112-44e62c64-PIPE-SEG-4021"
    payload = {
        "reviewer_id": "INSP-7801",
        "reviewer_name": "S. Ray",
        "reviewer_comments": "Updated estimate",
        "edited_work_order": {
            "estimated_cost": 4500.0,
            "suggested_team": "Specialist Integrity Team"
        }
    }
    response = client.put(f"/api/v1/reviews/{review_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["edited_work_order"]["estimated_cost"] == 4500.0
    assert data["edited_work_order"]["suggested_team"] == "Specialist Integrity Team"


def test_request_revision_api():
    review_id = "rev-insp-11112-44e62c64-PIPE-SEG-4021"
    payload = {
        "reviewer_id": "INSP-7801",
        "reviewer_name": "S. Ray",
        "comments": "Need supplementary ultrasonic shear wave inspection data."
    }
    response = client.post(f"/api/v1/reviews/{review_id}/request-revision", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REVISION_REQUESTED"


def test_approve_review_api():
    review_id = "rev-insp-11112-44e62c64-PIPE-SEG-4021"
    payload = {
        "reviewer_id": "INSP-7801",
        "reviewer_name": "S. Ray",
        "comments": "Work order formally authorized following engineering review."
    }
    response = client.post(f"/api/v1/reviews/{review_id}/approve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"
    assert data["reviewed_at"] is not None


def test_get_review_audit_trail_api():
    review_id = "rev-insp-11112-44e62c64-PIPE-SEG-4021"
    response = client.get(f"/api/v1/reviews/{review_id}/audit")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert any(log["event_type"] == "WORK_ORDER_APPROVED" for log in data)


def test_get_raw_and_overlay_images_api():
    res_raw = client.get("/api/v1/images/raw/11112.jpg")
    assert res_raw.status_code == 200
    assert res_raw.headers["content-type"] in ("image/jpeg", "image/png")
    assert len(res_raw.content) > 1000

    res_overlay = client.get("/api/v1/images/overlay/11112.jpg")
    assert res_overlay.status_code == 200
    assert res_overlay.headers["content-type"] in ("image/jpeg", "image/png")
    assert len(res_overlay.content) > 1000


def test_review_not_found_returns_404():
    response = client.get("/api/v1/reviews/non-existent-review-999")
    assert response.status_code == 404
