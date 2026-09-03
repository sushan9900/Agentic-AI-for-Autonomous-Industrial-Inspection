"""
Phase 6B Multi-Inspection Trend Analysis Test Suite.
Verifies multi-inspection time series, defect progression, severity progression,
risk score trajectories, recurrence patterns, inspection frequency, deterioration status,
evidence sufficiency, source traceability, fail-safe degradation, and safety invariants.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from backend.app.agents.inspection_agent import InspectionDecisionAgent
from backend.app.agents.prompts import AgentPromptBuilder
from backend.app.database.session import SessionLocal
from backend.app.schemas.inspection_history import (
    HistoricalInspectionContext,
    HistoricalInspectionRecord,
    HistoricalSummary,
)
from backend.app.schemas.inspection_trend import (
    DefectObservationPoint,
    InspectionIntervalPoint,
    InspectionTrendAnalysis,
    RiskScoreObservationPoint,
    SeverityObservationPoint,
)
from backend.app.services.inspection_history import InspectionHistoryService
from backend.app.services.inspection_trend import (
    InspectionTrendService,
    inspection_trend_service,
)
from backend.app.tools.get_inspection_history import GetInspectionHistoryTool
from vision.schemas.evidence import (
    DetectionEvidence,
    DetectionSummary,
    InspectionStatus,
    ModelProvenance,
    NormalizedBoundingBox,
    ProcessingTrace,
    QualityAssessment,
    SeverityFeatures,
    SourceImageProvenance,
    VisionEvidence,
)


@pytest.fixture(scope="module")
def db_session():
    """Provides a database session for read tests."""
    session = SessionLocal()
    yield session
    session.close()


def _make_dummy_evidence(defect_type: str = "crack", confidence: float = 0.92) -> VisionEvidence:
    """Helper to build a valid VisionEvidence object for agent integration testing."""
    return VisionEvidence(
        schema_version="1.0",
        inspection_id="INSP-TREND-TEST-01",
        component_id="PIPE-SEG-4021",
        status=InspectionStatus.SUCCESS,
        source_image=SourceImageProvenance(
            filename="trend_test_image.jpg",
            file_extension=".jpg",
            width=640,
            height=480,
            channels=3,
            file_size_bytes=50000,
            sha256_hash="1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff"
        ),
        model=ModelProvenance(
            model_name="YOLO11n-seg",
            model_architecture="YOLO11n-seg",
            model_version="1.0.0",
            checkpoint_identifier="best.pt",
            checkpoint_sha256="aabbcc",
            framework="ultralytics",
            framework_version="8.4.136",
            confidence_threshold=0.25,
            input_size=[640, 640],
            device="cpu"
        ),
        summary=DetectionSummary(
            detection_count=1,
            max_confidence=confidence,
            mean_confidence=confidence,
            min_confidence=confidence
        ),
        detections=[
            DetectionEvidence(
                detection_id="det-001",
                defect_type=defect_type,
                confidence=confidence,
                bounding_box=NormalizedBoundingBox(
                    x_pixel=64.0,
                    y_pixel=48.0,
                    width_pixel=256.0,
                    height_pixel=192.0,
                    x_norm=0.1,
                    y_norm=0.1,
                    width_norm=0.4,
                    height_norm=0.4
                ),
                severity_features=SeverityFeatures(
                    affected_area_percentage=8.5,
                    crack_length_pixels=145.0,
                    crack_width_estimate_pixels=12.0,
                    location_type="SURFACE"
                )
            )
        ],
        quality=QualityAssessment(
            brightness_mean=130.0,
            contrast_std=50.0,
            blur_score=200.0,
            blur_detected=False,
            low_contrast_detected=False,
            underexposed=False,
            overexposed=False,
            warnings=[]
        ),
        processing=ProcessingTrace(
            validation_ms=1.0,
            preprocessing_ms=2.0,
            inference_ms=30.0,
            postprocessing_ms=3.0,
            evidence_construction_ms=1.0,
            total_execution_ms=37.0
        )
    )


# ---------------------------------------------------------------------------
# TEST 1: Trend Schema Conformance
# ---------------------------------------------------------------------------
def test_trend_schema():
    """Validates that InspectionTrendAnalysis serializes cleanly and enforces field constraints."""
    now = datetime.now(timezone.utc)
    point = DefectObservationPoint(
        timestamp=now,
        inspection_id="INSP-01",
        defect_type="crack",
        defect_count=1,
        source_record_id="rec-01"
    )
    analysis = InspectionTrendAnalysis(
        asset_id="ASSET-01",
        component_id="COMP-01",
        inspection_count=1,
        defect_series=[point],
        trend_summary_explanation="Test analysis summary"
    )
    dump = analysis.model_dump(mode="json")
    assert dump["asset_id"] == "ASSET-01"
    assert dump["inspection_count"] == 1
    assert len(dump["defect_series"]) == 1
    assert dump["defect_trend"] == "INSUFFICIENT_HISTORY"


# ---------------------------------------------------------------------------
# TEST 2: Defect Progression - INCREASING
# ---------------------------------------------------------------------------
def test_defect_progression_increasing():
    """Verifies that increasing defect counts produce INCREASING defect trend."""
    now = datetime.now(timezone.utc)
    series = [
        DefectObservationPoint(timestamp=now - timedelta(days=30), inspection_id="I-1", defect_count=1, source_record_id="R-1"),
        DefectObservationPoint(timestamp=now, inspection_id="I-2", defect_count=3, source_record_id="R-2")
    ]
    trend, expl = inspection_trend_service.analyze_defect_progression(series)
    assert trend == "INCREASING"
    assert "increased from 1 to 3" in expl


# ---------------------------------------------------------------------------
# TEST 3: Defect Progression - STABLE
# ---------------------------------------------------------------------------
def test_defect_progression_stable():
    """Verifies that unchanged defect counts produce STABLE defect trend."""
    now = datetime.now(timezone.utc)
    series = [
        DefectObservationPoint(timestamp=now - timedelta(days=30), inspection_id="I-1", defect_count=2, source_record_id="R-1"),
        DefectObservationPoint(timestamp=now, inspection_id="I-2", defect_count=2, source_record_id="R-2")
    ]
    trend, expl = inspection_trend_service.analyze_defect_progression(series)
    assert trend == "STABLE"
    assert "consistent at 2" in expl


# ---------------------------------------------------------------------------
# TEST 4: Defect Progression - DECREASING
# ---------------------------------------------------------------------------
def test_defect_progression_decreasing():
    """Verifies that reduced defect counts produce DECREASING defect trend."""
    now = datetime.now(timezone.utc)
    series = [
        DefectObservationPoint(timestamp=now - timedelta(days=30), inspection_id="I-1", defect_count=4, source_record_id="R-1"),
        DefectObservationPoint(timestamp=now, inspection_id="I-2", defect_count=1, source_record_id="R-2")
    ]
    trend, expl = inspection_trend_service.analyze_defect_progression(series)
    assert trend == "DECREASING"
    assert "decreased from 4 to 1" in expl


# ---------------------------------------------------------------------------
# TEST 5: Severity Progression (Ordinal Ranking)
# ---------------------------------------------------------------------------
def test_severity_progression():
    """Verifies categorical severity progression: LOW (1) -> MEDIUM (2) -> HIGH (3) -> CRITICAL (4)."""
    now = datetime.now(timezone.utc)
    # Worsening severity: LOW -> HIGH
    worsening = [
        SeverityObservationPoint(timestamp=now - timedelta(days=20), inspection_id="I-1", severity="LOW", severity_rank=1, source_record_id="R-1"),
        SeverityObservationPoint(timestamp=now, inspection_id="I-2", severity="HIGH", severity_rank=3, source_record_id="R-2")
    ]
    trend_w, expl_w = inspection_trend_service.analyze_severity_progression(worsening)
    assert trend_w == "INCREASING"
    assert "LOW (Rank 1) to HIGH (Rank 3)" in expl_w

    # Improving severity: CRITICAL -> MEDIUM
    improving = [
        SeverityObservationPoint(timestamp=now - timedelta(days=20), inspection_id="I-1", severity="CRITICAL", severity_rank=4, source_record_id="R-1"),
        SeverityObservationPoint(timestamp=now, inspection_id="I-2", severity="MEDIUM", severity_rank=2, source_record_id="R-2")
    ]
    trend_i, expl_i = inspection_trend_service.analyze_severity_progression(improving)
    assert trend_i == "DECREASING"
    assert "CRITICAL (Rank 4) to MEDIUM (Rank 2)" in expl_i

    # Stable severity: HIGH -> HIGH
    stable = [
        SeverityObservationPoint(timestamp=now - timedelta(days=20), inspection_id="I-1", severity="HIGH", severity_rank=3, source_record_id="R-1"),
        SeverityObservationPoint(timestamp=now, inspection_id="I-2", severity="HIGH", severity_rank=3, source_record_id="R-2")
    ]
    trend_s, _ = inspection_trend_service.analyze_severity_progression(stable)
    assert trend_s == "STABLE"


# ---------------------------------------------------------------------------
# TEST 6: Risk Trajectory Trajectory
# ---------------------------------------------------------------------------
def test_risk_trajectory():
    """Verifies that risk score delta >= 10 is INCREASING, <= -10 is DECREASING, within +-10 is STABLE."""
    now = datetime.now(timezone.utc)
    increasing = [
        RiskScoreObservationPoint(timestamp=now - timedelta(days=20), inspection_id="I-1", risk_score=40, risk_level="MEDIUM", source_record_id="D-1"),
        RiskScoreObservationPoint(timestamp=now, inspection_id="I-2", risk_score=65, risk_level="HIGH", source_record_id="D-2")
    ]
    t_inc, expl_inc = inspection_trend_service.analyze_risk_trajectory(increasing)
    assert t_inc == "INCREASING"
    assert "increased by 25 points" in expl_inc

    decreasing = [
        RiskScoreObservationPoint(timestamp=now - timedelta(days=20), inspection_id="I-1", risk_score=75, risk_level="HIGH", source_record_id="D-1"),
        RiskScoreObservationPoint(timestamp=now, inspection_id="I-2", risk_score=50, risk_level="MEDIUM", source_record_id="D-2")
    ]
    t_dec, expl_dec = inspection_trend_service.analyze_risk_trajectory(decreasing)
    assert t_dec == "DECREASING"
    assert "decreased by 25 points" in expl_dec

    stable = [
        RiskScoreObservationPoint(timestamp=now - timedelta(days=20), inspection_id="I-1", risk_score=50, risk_level="MEDIUM", source_record_id="D-1"),
        RiskScoreObservationPoint(timestamp=now, inspection_id="I-2", risk_score=55, risk_level="MEDIUM", source_record_id="D-2")
    ]
    t_st, _ = inspection_trend_service.analyze_risk_trajectory(stable)
    assert t_st == "STABLE"


# ---------------------------------------------------------------------------
# TEST 7: Recurrence Detection (Intermittent Reappearance)
# ---------------------------------------------------------------------------
def test_recurrence_detection():
    """Verifies that a defect disappearing and reappearing is classified as RECURRENT."""
    now = datetime.now(timezone.utc)
    records = [
        HistoricalInspectionRecord(
            inspection_id="I-1", asset_id="A-1", inspection_timestamp=now - timedelta(days=60),
            defect_type="crack", source_record_id="1", similarity_reason="test"
        ),
        HistoricalInspectionRecord(
            inspection_id="I-2", asset_id="A-1", inspection_timestamp=now - timedelta(days=30),
            defect_type=None, source_record_id="2", similarity_reason="test"  # Clean inspection
        ),
        HistoricalInspectionRecord(
            inspection_id="I-3", asset_id="A-1", inspection_timestamp=now,
            defect_type="crack", source_record_id="3", similarity_reason="test"  # Reappeared
        ),
    ]
    pattern, count, expl = inspection_trend_service.analyze_recurrence_pattern(records, "crack")
    assert pattern == "RECURRENT"
    assert count == 2
    assert "non-consecutive" in expl


# ---------------------------------------------------------------------------
# TEST 8: Persistent Defect Detection (Consecutive Observations)
# ---------------------------------------------------------------------------
def test_persistent_defect_detection():
    """Verifies that a defect observed consecutively across all inspections is classified as PERSISTENT."""
    now = datetime.now(timezone.utc)
    records = [
        HistoricalInspectionRecord(
            inspection_id="I-1", asset_id="A-1", inspection_timestamp=now - timedelta(days=60),
            defect_type="crack", source_record_id="1", similarity_reason="test"
        ),
        HistoricalInspectionRecord(
            inspection_id="I-2", asset_id="A-1", inspection_timestamp=now - timedelta(days=30),
            defect_type="crack", source_record_id="2", similarity_reason="test"
        ),
        HistoricalInspectionRecord(
            inspection_id="I-3", asset_id="A-1", inspection_timestamp=now,
            defect_type="crack", source_record_id="3", similarity_reason="test"
        ),
    ]
    pattern, count, expl = inspection_trend_service.analyze_recurrence_pattern(records, "crack")
    assert pattern == "PERSISTENT"
    assert count == 3
    assert "consecutive chronological inspections" in expl


# ---------------------------------------------------------------------------
# TEST 9: Inspection Intervals & Frequency
# ---------------------------------------------------------------------------
def test_inspection_intervals():
    """Verifies calculation of intervals between inspections and frequency acceleration detection."""
    series = [
        InspectionIntervalPoint(from_inspection_id="I-1", to_inspection_id="I-2", interval_days=90.0),
        InspectionIntervalPoint(from_inspection_id="I-2", to_inspection_id="I-3", interval_days=30.0),  # Accelerated
    ]
    avg_int, min_int, max_int, freq_trend, expl = inspection_trend_service.analyze_inspection_intervals(series)
    assert avg_int == 60.0
    assert min_int == 30.0
    assert max_int == 90.0
    assert freq_trend == "FREQUENCY_INCREASING"
    assert "shorter than prior average" in expl


# ---------------------------------------------------------------------------
# TEST 10: Insufficient History Handling
# ---------------------------------------------------------------------------
def test_insufficient_history():
    """Verifies that fewer than 2 records safely return INSUFFICIENT_HISTORY across all sub-analyzers."""
    t_def, _ = inspection_trend_service.analyze_defect_progression([])
    t_sev, _ = inspection_trend_service.analyze_severity_progression([])
    t_rsk, _ = inspection_trend_service.analyze_risk_trajectory([])
    pat, cnt, _ = inspection_trend_service.analyze_recurrence_pattern([], "crack")
    avg_int, _, _, freq, _ = inspection_trend_service.analyze_inspection_intervals([])

    assert t_def == "INSUFFICIENT_HISTORY"
    assert t_sev == "INSUFFICIENT_HISTORY"
    assert t_rsk == "INSUFFICIENT_HISTORY"
    assert pat == "INSUFFICIENT_HISTORY"
    assert cnt == 0
    assert avg_int is None
    assert freq == "INSUFFICIENT_HISTORY"


# ---------------------------------------------------------------------------
# TEST 11: Missing Measurements Graceful Degradation
# ---------------------------------------------------------------------------
def test_missing_measurements():
    """Verifies that records with missing severity or risk scores process safely without crashing."""
    now = datetime.now(timezone.utc)
    records = [
        HistoricalInspectionRecord(
            inspection_id="I-1", asset_id="A-1", inspection_timestamp=now - timedelta(days=20),
            defect_type=None, severity=None, source_record_id="1", similarity_reason="test"
        ),
        HistoricalInspectionRecord(
            inspection_id="I-2", asset_id="A-1", inspection_timestamp=now,
            defect_type="crack", severity="HIGH", source_record_id="2", similarity_reason="test"
        )
    ]
    analysis = inspection_trend_service.analyze_trends(
        records=records,
        decisions=[],
        asset_id="A-1",
        defect_type="crack"
    )
    assert analysis.inspection_count == 2
    assert analysis.risk_trend == "INSUFFICIENT_HISTORY"  # No decisions provided
    assert analysis.severity_trend == "INSUFFICIENT_HISTORY"  # Only 1 record had severity


# ---------------------------------------------------------------------------
# TEST 12: Source Traceability
# ---------------------------------------------------------------------------
def test_source_traceability():
    """Verifies that all time series points preserve their source inspection IDs and database record IDs."""
    now = datetime.now(timezone.utc)
    records = [
        HistoricalInspectionRecord(
            inspection_id="INSP-TRACE-1", asset_id="A-1", inspection_timestamp=now - timedelta(days=10),
            defect_type="crack", severity="MEDIUM", source_record_id="DB-REC-101", similarity_reason="test"
        ),
        HistoricalInspectionRecord(
            inspection_id="INSP-TRACE-2", asset_id="A-1", inspection_timestamp=now,
            defect_type="crack", severity="HIGH", source_record_id="DB-REC-102", similarity_reason="test"
        )
    ]
    decisions = [
        {"decision_id": "DEC-101", "inspection_id": "INSP-TRACE-1", "risk_score": 45, "created_at": (now - timedelta(days=10)).isoformat()},
        {"decision_id": "DEC-102", "inspection_id": "INSP-TRACE-2", "risk_score": 60, "created_at": now.isoformat()},
    ]
    analysis = inspection_trend_service.analyze_trends(
        records=records,
        decisions=decisions,
        asset_id="A-1",
        defect_type="crack"
    )

    for pt in analysis.defect_series:
        assert pt.source_record_id.startswith("DB-REC-")
        assert pt.inspection_id.startswith("INSP-TRACE-")

    for pt in analysis.severity_series:
        assert pt.source_record_id.startswith("DB-REC-")

    for pt in analysis.risk_series:
        assert pt.source_record_id.startswith("DEC-")

    assert "INSP-TRACE-1" in analysis.source_inspection_ids
    assert "INSP-TRACE-2" in analysis.source_inspection_ids


# ---------------------------------------------------------------------------
# TEST 13: Deterioration Status Synthesis
# ---------------------------------------------------------------------------
def test_deterioration_status():
    """Verifies deterministic multi-signal synthesis for DETERIORATING, IMPROVING, RECURRENT_RISK, and STABLE."""
    # Deteriorating: increasing severity and risk
    det, expl_det = inspection_trend_service.evaluate_deterioration_status(
        evidence_sufficiency="SUFFICIENT",
        defect_trend="INCREASING",
        severity_trend="INCREASING",
        risk_trend="INCREASING",
        recurrence_pattern="PERSISTENT",
        latest_risk_score=75
    )
    assert det == "DETERIORATING"
    assert "Multi-signal deterioration" in expl_det

    # Improving: decreasing severity and risk
    imp, _ = inspection_trend_service.evaluate_deterioration_status(
        evidence_sufficiency="SUFFICIENT",
        defect_trend="DECREASING",
        severity_trend="DECREASING",
        risk_trend="DECREASING",
        recurrence_pattern="NO_RECURRENCE",
        latest_risk_score=25
    )
    assert imp == "IMPROVING"

    # Recurrent Risk: stable/moderate trends but persistent defect under elevated baseline risk
    rr, expl_rr = inspection_trend_service.evaluate_deterioration_status(
        evidence_sufficiency="SUFFICIENT",
        defect_trend="STABLE",
        severity_trend="STABLE",
        risk_trend="STABLE",
        recurrence_pattern="PERSISTENT",
        latest_risk_score=65
    )
    assert rr == "RECURRENT_RISK"
    assert "elevated risk baseline" in expl_rr

    # Stable: everything stable with low risk
    stb, _ = inspection_trend_service.evaluate_deterioration_status(
        evidence_sufficiency="SUFFICIENT",
        defect_trend="STABLE",
        severity_trend="STABLE",
        risk_trend="STABLE",
        recurrence_pattern="NO_RECURRENCE",
        latest_risk_score=30
    )
    assert stb == "STABLE"


# ---------------------------------------------------------------------------
# TEST 14: Evidence Sufficiency Classification
# ---------------------------------------------------------------------------
def test_evidence_sufficiency():
    """Verifies evidence sufficiency rules: >=3 is SUFFICIENT, 2 is LIMITED, <2 is INSUFFICIENT."""
    assert inspection_trend_service.evaluate_evidence_sufficiency(3, 2, 2) == "SUFFICIENT"
    assert inspection_trend_service.evaluate_evidence_sufficiency(2, 2, 2) == "LIMITED"
    assert inspection_trend_service.evaluate_evidence_sufficiency(1, 1, 0) == "INSUFFICIENT"
    assert inspection_trend_service.evaluate_evidence_sufficiency(0, 0, 0) == "INSUFFICIENT"


# ---------------------------------------------------------------------------
# TEST 15: Database Failure Fail-Safe Handling
# ---------------------------------------------------------------------------
def test_database_failure():
    """Verifies that database failures or None sessions gracefully degrade to safe trends without exceptions."""
    svc = InspectionHistoryService()
    ctx = svc.build_historical_context(
        db=None,
        asset_id="ASSET-FAIL-SAFE",
        component_id="COMP-01"
    )
    assert ctx.has_history is False
    assert ctx.retrieval_metadata["status"] == "DB_UNAVAILABLE"
    assert ctx.trends is None


# ---------------------------------------------------------------------------
# TEST 16: CRITICAL SAFETY: Trend Cannot Override Authoritative Decision
# ---------------------------------------------------------------------------
def test_trend_cannot_override_current_decision(db_session: Session):
    """
    CRITICAL SAFETY INVARIANT:
    Even when historical trends indicate an IMPROVING condition or STABLE trend,
    the current physical in-flight vision evidence strictly dictates the authoritative risk score
    and operational action through DecisionPolicyEngine. Trends NEVER override policy.
    """
    evidence = _make_dummy_evidence(defect_type="crack", confidence=0.95)
    agent = InspectionDecisionAgent()

    # Create mock historical context with an artificially IMPROVING trend
    mock_history_ctx = HistoricalInspectionContext(
        has_history=True,
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        summary=HistoricalSummary(
            total_previous_inspections=5,
            risk_trend="DECREASING",
            trend_explanation="Artificially improving risk trend."
        ),
        recent_inspections=[],
        similar_inspections=[],
        previous_decisions=[],
        trends=InspectionTrendAnalysis(
            asset_id="ASSET-PL-01",
            component_id="PIPE-SEG-4021",
            inspection_count=5,
            defect_trend="DECREASING",
            severity_trend="DECREASING",
            risk_trend="DECREASING",
            deterioration_status="IMPROVING",
            evidence_sufficiency="SUFFICIENT",
            trend_summary_explanation="Historical trends indicate component improvement."
        ),
        retrieval_metadata={"status": "MOCK_TEST"}
    )

    mock_tool = MagicMock(spec=GetInspectionHistoryTool)
    mock_tool.execute.return_value = mock_history_ctx

    import sys
    mod = sys.modules["backend.app.agents.inspection_agent"]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(mod, "get_inspection_history_tool", mock_tool)

        decision = agent.run_inspection(
            inspection_id="INSP-TREND-TEST-01",
            asset_id="ASSET-PL-01",
            component_id="PIPE-SEG-4021",
            evidence=evidence,
            db=db_session
        )

        # Authoritative decision MUST remain CRITICAL based on physical crack evidence
        assert decision.risk_assessment["risk_score"] >= 80, "High severity crack must produce high risk"
        assert decision.operational_decision in ("URGENT_ENGINEERING_REVIEW", "PRIORITY_MAINTENANCE")
        assert decision.human_review_required is True
        assert decision.review_status == "PENDING_HUMAN_REVIEW"

        # Verify inspection_trends are attached as supporting context only
        assert decision.inspection_trends is not None
        assert decision.inspection_trends["deterioration_status"] == "IMPROVING"


# ---------------------------------------------------------------------------
# TEST 17: LLM Prompt Historical Trend Boundary
# ---------------------------------------------------------------------------
def test_llm_cannot_override_current_decision():
    """Verifies that AgentPromptBuilder isolates trends into non-authoritative supporting context."""
    evidence = _make_dummy_evidence()

    hist_context = {
        "summary": {
            "total_previous_inspections": 3,
            "risk_trend": "INCREASING"
        },
        "recent_inspections": [],
        "similar_inspections": [],
        "trends": {
            "defect_trend": "INCREASING",
            "severity_trend": "INCREASING",
            "risk_trend": "INCREASING",
            "recurrence_pattern": "PERSISTENT",
            "frequency_trend": "FREQUENCY_INCREASING",
            "deterioration_status": "DETERIORATING",
            "evidence_sufficiency": "SUFFICIENT",
            "trend_summary_explanation": "Component is deteriorating across 3 consecutive inspections."
        }
    }

    prompt = AgentPromptBuilder.build_prompt(
        evidence=evidence,
        asset_context={"asset_id": "ASSET-PL-01", "name": "Main Pipe Loop"},
        maintenance_history=[],
        severity_thresholds=[],
        similar_incidents=[],
        risk_assessment={"risk_score": 90, "risk_level": "CRITICAL"},
        operational_decision="URGENT_ENGINEERING_REVIEW",
        historical_context=hist_context
    )

    # 1. Must include the non-authoritative boundary notice and multi-inspection trends block
    assert "SUPPORTING_HISTORICAL_INSPECTION_CONTEXT" in prompt
    assert "INFORMATIONAL ONLY" in prompt
    assert "NON-AUTHORITATIVE" in prompt
    assert "multi_inspection_trends" in prompt
    assert "DETERIORATING" in prompt

    # 2. Must contain explicit negative instructions preventing LLM overrides
    assert "Historical inspection intelligence and multi-inspection trends are SUPPORTING evidence only" in prompt
    assert "NEVER use it to recalculate, lower, or raise the authoritative risk score" in prompt
    assert "DO NOT change or contradict the AUTHORITATIVE_SYSTEM_DECISION" in prompt
