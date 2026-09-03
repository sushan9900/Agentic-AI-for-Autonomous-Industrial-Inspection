"""Comprehensive unit and integration tests for Inspection Memory & Historical Intelligence (Phase 6A)."""

from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from backend.app.agents.inspection_agent import InspectionDecisionAgent
from backend.app.agents.prompts import AgentPromptBuilder
from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.database.models.component import Component
from backend.app.database.models.inspection import InspectionRecord
from backend.app.database.session import SessionLocal
from backend.app.schemas.inspection_history import (
    HistoricalInspectionContext,
    HistoricalInspectionRecord,
    HistoricalSummary,
)
from backend.app.services.inspection_history import (
    InspectionHistoryService,
    inspection_history_service,
)
from backend.app.tools.get_inspection_history import (
    GetInspectionHistoryTool,
    InspectionHistoryInput,
    get_inspection_history_tool,
)
from vision.schemas.evidence import (
    DetectionEvidence,
    DetectionSummary,
    InspectionStatus,
    ModelProvenance,
    NormalizedBoundingBox,
    ProcessingTrace,
    QualityAssessment,
    SourceImageProvenance,
    VisionEvidence,
)
from vision.schemas.evidence import (
    DetectionEvidence,
    DetectionSummary,
    InspectionStatus,
    ModelProvenance,
    NormalizedBoundingBox,
    ProcessingTrace,
    QualityAssessment,
    SourceImageProvenance,
    VisionEvidence,
)
from vision.schemas.inspection import SeverityFeatures


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
        inspection_id="INSP-HIST-TEST-01",
        component_id="PIPE-SEG-4021",
        status=InspectionStatus.SUCCESS,
        source_image=SourceImageProvenance(
            filename="hist_test_image.jpg",
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
# TEST 1: Asset History Retrieval
# ---------------------------------------------------------------------------
def test_asset_history_retrieval(db_session: Session):
    """Verifies retrieval of asset-level inspection records and correlated decision fields."""
    records = inspection_history_service.get_asset_history(
        db=db_session,
        asset_id="ASSET-PL-01",
        limit=10
    )
    assert isinstance(records, list)
    if records:
        r0 = records[0]
        assert isinstance(r0, HistoricalInspectionRecord)
        assert r0.asset_id == "ASSET-PL-01"
        assert r0.source_record_id is not None
        assert "ASSET-PL-01" in r0.similarity_reason


# ---------------------------------------------------------------------------
# TEST 2: Component History Retrieval
# ---------------------------------------------------------------------------
def test_component_history_retrieval(db_session: Session):
    """Verifies retrieval of component-specific historical inspection events."""
    records = inspection_history_service.get_component_history(
        db=db_session,
        component_id="PIPE-SEG-4021",
        limit=5
    )
    assert isinstance(records, list)
    for r in records:
        assert r.component_id == "PIPE-SEG-4021"
        assert "PIPE-SEG-4021" in r.similarity_reason


# ---------------------------------------------------------------------------
# TEST 3: Similar Inspection Retrieval
# ---------------------------------------------------------------------------
def test_similar_inspection_retrieval(db_session: Session):
    """Verifies deterministic similarity matching across component, asset, and fleet scopes."""
    similar = inspection_history_service.get_similar_inspections(
        db=db_session,
        defect_type="crack",
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        limit=5
    )
    assert isinstance(similar, list)
    for item in similar:
        assert isinstance(item, HistoricalInspectionRecord)
        assert item.source_record_id is not None
        assert "crack" in item.similarity_reason.lower()


# ---------------------------------------------------------------------------
# TEST 4: History Summary & Recurrence Detection
# ---------------------------------------------------------------------------
def test_history_summary(db_session: Session):
    """Verifies calculation of history summary metrics, recurrence flag, and critical event count."""
    context = inspection_history_service.build_historical_context(
        db=db_session,
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        defect_type="crack"
    )
    assert isinstance(context, HistoricalInspectionContext)
    assert context.asset_id == "ASSET-PL-01"
    assert isinstance(context.summary, HistoricalSummary)
    assert context.summary.total_previous_inspections >= 0
    assert context.summary.same_component_inspections >= 0
    assert isinstance(context.summary.recurring_defect_detected, bool)


# ---------------------------------------------------------------------------
# TEST 5: Deterministic Risk Trend (INCREASING, DECREASING, STABLE)
# ---------------------------------------------------------------------------
def test_risk_trend():
    """Verifies mathematical risk trend classification with sufficient records."""
    srv = InspectionHistoryService()

    # Increasing (delta >= 10)
    trend, expl = srv.calculate_risk_trend([50, 65, 80])
    assert trend == "INCREASING"
    assert "increased by 30 points" in expl

    # Decreasing (delta <= -10)
    trend, expl = srv.calculate_risk_trend([85, 70, 55])
    assert trend == "DECREASING"
    assert "decreased by 30 points" in expl

    # Stable (delta within +/- 10)
    trend, expl = srv.calculate_risk_trend([70, 75, 73])
    assert trend == "STABLE"
    assert "remained stable" in expl


# ---------------------------------------------------------------------------
# TEST 6: Insufficient History Handling
# ---------------------------------------------------------------------------
def test_insufficient_history():
    """Verifies that INSUFFICIENT_HISTORY is returned when fewer than 2 scores exist."""
    srv = InspectionHistoryService()

    trend, expl = srv.calculate_risk_trend([])
    assert trend == "INSUFFICIENT_HISTORY"

    trend, expl = srv.calculate_risk_trend([75])
    assert trend == "INSUFFICIENT_HISTORY"
    assert "Fewer than 2" in expl


# ---------------------------------------------------------------------------
# TEST 7: Missing Asset / No History Safe Degradation
# ---------------------------------------------------------------------------
def test_missing_history(db_session: Session):
    """Verifies that assets with zero historical records degrade gracefully without exceptions."""
    context = inspection_history_service.build_historical_context(
        db=db_session,
        asset_id="NON_EXISTENT_ASSET_XYZ",
        component_id="NON_EXISTENT_COMP_XYZ",
        defect_type="crack"
    )
    assert context.has_history is False
    assert context.summary.total_previous_inspections == 0
    assert context.summary.risk_trend == "INSUFFICIENT_HISTORY"
    assert context.recent_inspections == []
    assert context.previous_decisions == []


# ---------------------------------------------------------------------------
# TEST 8: Database Failure Safe Degradation
# ---------------------------------------------------------------------------
def test_database_failure():
    """Verifies fail-safe handling when database is None or raises unexpected exceptions."""
    # Case A: db is None
    ctx_none = inspection_history_service.build_historical_context(
        db=None,
        asset_id="ASSET-PL-01"
    )
    assert ctx_none.has_history is False
    assert ctx_none.retrieval_metadata.get("status") == "DB_UNAVAILABLE"
    assert ctx_none.summary.risk_trend == "INSUFFICIENT_HISTORY"

    # Case B: db raises exception
    mock_failing_db = MagicMock(spec=Session)
    mock_failing_db.query.side_effect = RuntimeError("Simulated PostgreSQL connection timeout")

    ctx_err = inspection_history_service.build_historical_context(
        db=mock_failing_db,
        asset_id="ASSET-PL-01"
    )
    assert ctx_err.has_history is False
    assert ctx_err.retrieval_metadata.get("status") == "ERROR"
    assert "Simulated PostgreSQL connection timeout" in ctx_err.retrieval_metadata.get("error_message", "")


# ---------------------------------------------------------------------------
# TEST 9: Historical Records Traceability
# ---------------------------------------------------------------------------
def test_historical_records_traceability(db_session: Session):
    """Verifies all returned historical inspection records contain traceable non-empty database IDs."""
    context = inspection_history_service.build_historical_context(
        db=db_session,
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021"
    )
    for rec in context.recent_inspections:
        assert rec.source_record_id, "Source record ID must not be empty"
        assert rec.inspection_id, "Inspection ID must be present"
        assert rec.similarity_reason, "Similarity reason must be documented"

    for sim in context.similar_inspections:
        assert sim.source_record_id, "Similar inspection source record ID must be present"
        assert sim.inspection_id, "Similar inspection ID must be present"


# ---------------------------------------------------------------------------
# TEST 10: Historical Intelligence Cannot Override Authoritative Decision
# ---------------------------------------------------------------------------
def test_history_cannot_override_authoritative_decision(db_session: Session):
    """
    CRITICAL SAFETY TEST:
    Even when historical context presents a favorable or decreasing risk trend,
    the current in-flight physical evidence dictates the authoritative risk score
    and operational action through DecisionPolicyEngine. History CANNOT override policy.
    """
    evidence = _make_dummy_evidence(defect_type="crack", confidence=0.95)
    agent = InspectionDecisionAgent()

    # Mock historical context with artificially low risk trend
    mock_history_ctx = HistoricalInspectionContext(
        has_history=True,
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        summary=HistoricalSummary(
            total_previous_inspections=5,
            same_component_inspections=3,
            previous_critical_events=0,
            recurring_defect_detected=False,
            latest_previous_risk_score=10,
            risk_trend="DECREASING",
            trend_explanation="Artificially low historical trend for safety testing."
        ),
        recent_inspections=[],
        similar_inspections=[],
        previous_decisions=[],
        retrieval_metadata={"status": "MOCK_TEST"}
    )

    mock_tool = MagicMock(spec=GetInspectionHistoryTool)
    mock_tool.execute.return_value = mock_history_ctx

    import sys
    mod = sys.modules["backend.app.agents.inspection_agent"]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(mod, "get_inspection_history_tool", mock_tool)

        decision = agent.run_inspection(
            inspection_id="INSP-HIST-TEST-01",
            asset_id="ASSET-PL-01",
            component_id="PIPE-SEG-4021",
            evidence=evidence,
            db=db_session
        )

        # Authoritative decision MUST be based on the physical critical crack, NOT the historical trend
        assert decision.risk_assessment["risk_score"] >= 80, "High severity physical crack must produce high risk"
        assert decision.operational_decision in ("URGENT_ENGINEERING_REVIEW", "PRIORITY_MAINTENANCE")
        assert decision.human_review_required is True
        assert decision.review_status == "PENDING_HUMAN_REVIEW"

        # Verify historical context is attached as supporting evidence only
        assert decision.historical_context is not None
        assert decision.historical_context["summary"]["risk_trend"] == "DECREASING"


# ---------------------------------------------------------------------------
# TEST 11: LLM Prompt Historical Context Boundary
# ---------------------------------------------------------------------------
def test_llm_cannot_override_historical_boundary():
    """Verifies that the prompt builder explicitly isolates historical context and enforces non-authoritative boundaries."""
    evidence = _make_dummy_evidence()

    hist_context = {
        "summary": {
            "total_previous_inspections": 4,
            "recurring_defect_detected": True,
            "risk_trend": "INCREASING"
        },
        "recent_inspections": [
            {"inspection_id": "INSP-PAST-01", "defect_type": "crack", "risk_score": 65}
        ],
        "similar_inspections": []
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

    # 1. Must include the non-authoritative boundary notice
    assert "SUPPORTING_HISTORICAL_INSPECTION_CONTEXT" in prompt
    assert "INFORMATIONAL ONLY" in prompt
    assert "NON-AUTHORITATIVE" in prompt

    # 2. Must contain explicit negative instructions preventing LLM overrides
    assert "NEVER use it to recalculate, lower, or raise the authoritative risk score" in prompt
    assert "DO NOT change or contradict the AUTHORITATIVE_SYSTEM_DECISION" in prompt


# ---------------------------------------------------------------------------
# TEST 12: Tool Execution Contract
# ---------------------------------------------------------------------------
def test_get_inspection_history_tool_execution(db_session: Session):
    """Verifies that GetInspectionHistoryTool conforms to BaseAgentTool contract."""
    tool = get_inspection_history_tool
    assert tool.name == "get_inspection_history"
    assert "inspection track records" in tool.description.lower()

    inp = InspectionHistoryInput(
        asset_id="ASSET-PL-01",
        component_id="PIPE-SEG-4021",
        defect_type="crack"
    )
    out = tool.execute(inp, db=db_session)
    assert isinstance(out, HistoricalInspectionContext)
    assert out.asset_id == "ASSET-PL-01"
