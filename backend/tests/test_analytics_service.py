"""Unit tests for HistoryService, TrendService, RiskService, and TimelineService (Phase 3A)."""

from datetime import datetime, timezone
import pytest
from backend.app.database.session import SessionLocal
from backend.app.services.analytics import (
    history_service,
    risk_service,
    timeline_service,
    trend_service,
)


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_history_service_inspections_and_recency(db_session):
    inspections = history_service.get_asset_inspections(db_session, "ASSET-PL-01")
    assert len(inspections) >= 2

    latest = history_service.get_latest_inspection(db_session, "ASSET-PL-01")
    assert latest is not None

    previous = history_service.get_previous_inspection(db_session, "ASSET-PL-01")
    assert previous is not None
    assert latest.inspection_timestamp >= previous.inspection_timestamp


def test_history_service_defects(db_session):
    defects = history_service.get_asset_defects(db_session, "ASSET-PL-01")
    assert len(defects) >= 3
    assert all(d.asset_id == "ASSET-PL-01" for d in defects)
    assert any(d.defect_type == "crack" for d in defects)


def test_trend_service_calculations(db_session):
    trends = trend_service.calculate_asset_trends(db_session, "ASSET-PL-01")
    assert trends.asset_id == "ASSET-PL-01"
    assert trends.total_inspections >= 2
    assert trends.total_defects_detected >= 3
    assert trends.defect_count_trend in ("INCREASING", "DECREASING", "STABLE")
    assert len(trends.time_series) >= 2


def test_risk_service_deterministic_scoring(db_session):
    risk = risk_service.calculate_asset_risk(db_session, "ASSET-PL-01")
    assert risk.asset_id == "ASSET-PL-01"
    assert 0 <= risk.risk_score <= 100
    assert risk.risk_band in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    assert len(risk.contributing_factors) >= 1
    assert "AI-assisted operational risk indicator" in risk.disclaimer


def test_timeline_service_chronological_aggregation(db_session):
    timeline = timeline_service.build_asset_timeline(db_session, "ASSET-PL-01")
    assert timeline.asset_id == "ASSET-PL-01"
    assert timeline.events_count >= 5
    # Verify chronological ordering (descending)
    timestamps = [e.timestamp for e in timeline.events]
    assert timestamps == sorted(timestamps, reverse=True)
    
    event_types = {e.event_type for e in timeline.events}
    assert "INSPECTION" in event_types
    assert "DEFECT_DETECTED" in event_types
