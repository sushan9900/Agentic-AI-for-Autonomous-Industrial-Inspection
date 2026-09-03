"""Evidence Request Planner Service (Phase 8E)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session

from backend.app.database.models.agent_decision import AgentDecisionModel
from backend.app.schemas.evidence_request import (
    EvidenceRequest,
    EvidenceRequestPlanResponse,
    EvidenceRequestType,
)


class InspectionDecisionNotFoundError(Exception):
    """Raised when the referenced inspection decision does not exist."""
    pass


class EvidenceRequestPlanner:
    """
    Analyzes visual uncertainty and unobserved diagnostic gaps to generate structured evidence requests.
    Never claims requested evidence already exists; requires human approval before dispatch.
    """

    def plan_evidence_requests(
        self,
        db: Session,
        inspection_id: str
    ) -> EvidenceRequestPlanResponse:
        """
        Generates a targeted evidence request plan for an inspection.
        """
        decision = (
            db.query(AgentDecisionModel)
            .filter(AgentDecisionModel.inspection_id == inspection_id)
            .first()
        )
        if not decision:
            raise InspectionDecisionNotFoundError(f"Inspection decision for '{inspection_id}' was not found.")

        ev_ref = decision.evidence_reference or {}
        gaps = decision.evidence_gaps or []
        metrics = decision.execution_metrics or {}
        inv_plan = metrics.get("investigation_plan") or {}
        unobserved = inv_plan.get("unobserved_gaps") or []

        combined_gaps = list(set(gaps + unobserved))
        component_id = ev_ref.get("component_id") or decision.asset_id
        requests: List[EvidenceRequest] = []
        now = datetime.now(timezone.utc)

        # 1. Evaluate unobserved physical gaps
        for gap in combined_gaps:
            gap_lower = gap.lower()
            req_id = f"req-ev-{inspection_id}-{uuid.uuid4().hex[:6]}"

            if any(term in gap_lower for term in ("depth", "thickness", "wall")):
                requests.append(
                    EvidenceRequest(
                        request_id=req_id,
                        inspection_id=inspection_id,
                        asset_id=decision.asset_id,
                        component_id=component_id,
                        request_type=EvidenceRequestType.COMPONENT_CLOSEUP,
                        reason=f"Defect dimensional analysis requires macro closeup to quantify wall depth/loss ({gap}).",
                        evidence_gap=gap,
                        required=True,
                        human_approval_required=True,
                        created_at=now
                    )
                )
            elif any(term in gap_lower for term in ("angle", "coverage", "obscured")):
                requests.append(
                    EvidenceRequest(
                        request_id=req_id,
                        inspection_id=inspection_id,
                        asset_id=decision.asset_id,
                        component_id=component_id,
                        request_type=EvidenceRequestType.ALTERNATE_VIEW,
                        reason=f"Surface perspective is partially obscured or unobserved from primary visual angle ({gap}).",
                        evidence_gap=gap,
                        required=True,
                        human_approval_required=True,
                        created_at=now
                    )
                )
            else:
                requests.append(
                    EvidenceRequest(
                        request_id=req_id,
                        inspection_id=inspection_id,
                        asset_id=decision.asset_id,
                        component_id=component_id,
                        request_type=EvidenceRequestType.ADDITIONAL_IMAGE,
                        reason=f"Supplemental visual evidence required to resolve unobserved diagnostic factor ({gap}).",
                        evidence_gap=gap,
                        required=False,
                        human_approval_required=True,
                        created_at=now
                    )
                )

        # 2. Check for low-confidence detections
        detections = ev_ref.get("detections") or []
        for det in detections:
            conf = det.get("confidence", 1.0)
            if conf < 0.70:
                req_id = f"req-ev-conf-{inspection_id}-{uuid.uuid4().hex[:6]}"
                requests.append(
                    EvidenceRequest(
                        request_id=req_id,
                        inspection_id=inspection_id,
                        asset_id=decision.asset_id,
                        component_id=component_id,
                        request_type=EvidenceRequestType.HIGHER_RESOLUTION_IMAGE,
                        reason=(
                            f"Detection on component '{component_id}' has marginal confidence ({conf:.2f}). "
                            "Higher-resolution re-acquisition advised to disambiguate surface artifacts."
                        ),
                        evidence_gap=f"Low detection confidence ({conf:.2f})",
                        required=False,
                        human_approval_required=True,
                        created_at=now
                    )
                )

        return EvidenceRequestPlanResponse(
            inspection_id=inspection_id,
            total_requests=len(requests),
            requests=requests
        )


evidence_request_planner = EvidenceRequestPlanner()
