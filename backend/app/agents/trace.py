"""Agent operational trace recorder for auditable decision workflows (Phase 3B/3C)."""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
from backend.app.schemas.agent_decision import TraceEvent


class TraceRecorder:
    """Helper to record and time sequential execution stages."""

    def __init__(self):
        self.events: List[TraceEvent] = []
        self._step_counter = 0

    def record_step(
        self,
        stage: str,
        result_summary: str,
        tool: Optional[str] = None,
        input_summary: Optional[Dict[str, Any]] = None,
        decision_impact: Optional[str] = None,
        status: str = "completed",
        duration_ms: Optional[float] = None
    ) -> TraceEvent:
        """Appends an observable trace event."""
        self._step_counter += 1
        event = TraceEvent(
            step=self._step_counter,
            stage=stage,
            tool=tool,
            input_summary=input_summary,
            result_summary=result_summary,
            decision_impact=decision_impact,
            status=status,
            duration_ms=round(duration_ms, 2) if duration_ms is not None else None,
            timestamp=datetime.now(timezone.utc)
        )
        self.events.append(event)
        return event

    def get_events(self) -> List[TraceEvent]:
        """Returns the full list of recorded trace events."""
        return self.events
