"""Draft work order synthesis and lifecycle safety helpers (Phase 2C)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.schemas.agent_assessment import DraftWorkOrder
from backend.app.schemas.decision import InspectionPriority


class WorkOrderSynthesizer:
    """Safely synthesizes draft work orders with strict human-in-the-loop approval constraints."""

    @staticmethod
    def create_draft(
        draft_id: str,
        component_id: str,
        inspection_reference: str,
        priority: str,
        recommended_action: str,
        justification: str,
        required_inspection: str,
        suggested_team: str,
        estimated_downtime_hours: Optional[float] = None,
        estimated_cost: Optional[float] = None,
        supporting_evidence: Optional[List[str]] = None,
        historical_support: Optional[List[str]] = None,
        uncertainty: Optional[str] = None
    ) -> DraftWorkOrder:
        """
        Creates a structured DraftWorkOrder with mandatory 'PENDING_HUMAN_REVIEW' status.
        Never sets status to 'APPROVED'.
        """
        return DraftWorkOrder(
            schema_version="1.0",
            draft_id=draft_id,
            component_id=component_id,
            inspection_reference=inspection_reference,
            priority=priority,
            recommended_action=recommended_action,
            justification=justification,
            required_inspection=required_inspection,
            suggested_team=suggested_team,
            estimated_downtime_hours=estimated_downtime_hours,
            estimated_cost=estimated_cost,
            supporting_evidence=supporting_evidence or [],
            historical_support=historical_support or [],
            uncertainty=uncertainty or "Human inspector review required before work order authorization.",
            approval_status="PENDING_HUMAN_REVIEW",
            generated_at=datetime.now(timezone.utc).isoformat(),
            generated_by="InspectionReasoningAgent"
        )
