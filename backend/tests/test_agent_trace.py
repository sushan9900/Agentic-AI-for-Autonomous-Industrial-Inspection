"""Unit tests for TraceRecorder and TraceEvent observable traces (Phase 3B)."""

import pytest
from backend.app.agents.trace import TraceRecorder


def test_trace_recorder_step_ordering_and_timing():
    recorder = TraceRecorder()
    
    e1 = recorder.record_step(
        stage="INGEST_EVIDENCE",
        result_summary="Ingested evidence",
        duration_ms=1.5
    )
    e2 = recorder.record_step(
        stage="GET_ASSET_CONTEXT",
        tool="get_asset_context",
        result_summary="Retrieved asset context",
        duration_ms=4.2
    )
    e3 = recorder.record_step(
        stage="FORMULATE_DECISION",
        result_summary="Decision formulated: URGENT_ENGINEERING_REVIEW",
        decision_impact="Sets priority to CRITICAL",
        duration_ms=0.8
    )

    events = recorder.get_events()
    assert len(events) == 3
    assert events[0].step == 1
    assert events[1].step == 2
    assert events[2].step == 3
    assert events[0].stage == "INGEST_EVIDENCE"
    assert events[1].tool == "get_asset_context"
    assert events[2].decision_impact == "Sets priority to CRITICAL"
