"""Unified chronological timeline aggregation service (Phase 3A)."""

from datetime import timezone
from typing import List
from sqlalchemy import desc
from sqlalchemy.orm import Session
from backend.app.database.models.component import Component
from backend.app.database.models.defect import DefectRecord
from backend.app.database.models.incident import IncidentRecord
from backend.app.database.models.inspection import InspectionRecord
from backend.app.database.models.maintenance import MaintenanceRecord
from backend.app.database.models.review import InspectionReview, ReviewAuditLog
from backend.app.database.models.work_order import WorkOrder
from backend.app.schemas.analytics import AssetTimelineResponse, TimelineEvent


class TimelineService:
    """Aggregates chronological lifecycle events for an industrial asset without mutating source records."""

    def build_asset_timeline(self, db: Session, asset_id: str) -> AssetTimelineResponse:
        components = db.query(Component).filter(Component.asset_id == asset_id).all()
        comp_ids = [c.component_id for c in components]
        comp_types = [c.component_type for c in components]

        events: List[TimelineEvent] = []

        # 1. Maintenance Events
        maints = db.query(MaintenanceRecord).filter(MaintenanceRecord.component_id.in_(comp_ids)).all()
        for m in maints:
            events.append(
                TimelineEvent(
                    event_id=f"evt-maint-{m.maintenance_id}",
                    asset_id=asset_id,
                    component_id=m.component_id,
                    event_type="MAINTENANCE_PERFORMED",
                    timestamp=m.performed_at.replace(tzinfo=timezone.utc) if m.performed_at.tzinfo is None else m.performed_at,
                    title=f"Maintenance: {m.maintenance_type}",
                    description=f"{m.action_taken} Findings: {m.findings or 'None'}",
                    source_reference=f"maintenance_records/{m.maintenance_id}",
                    metadata={"cost": m.cost, "downtime_hours": m.downtime_hours, "team": m.technician_team}
                )
            )

        # 2. Inspection Events
        inspections = db.query(InspectionRecord).filter(InspectionRecord.component_id.in_(comp_ids)).all()
        for i in inspections:
            events.append(
                TimelineEvent(
                    event_id=f"evt-insp-{i.inspection_id}",
                    asset_id=asset_id,
                    component_id=i.component_id,
                    event_type="INSPECTION",
                    timestamp=i.inspection_timestamp.replace(tzinfo=timezone.utc) if i.inspection_timestamp.tzinfo is None else i.inspection_timestamp,
                    title=f"Inspection: {i.inspection_method} ({i.severity})",
                    description=f"Findings: {i.findings} (Defect: {i.defect_type}, Confidence: {i.confidence})",
                    source_reference=f"inspection_records/{i.inspection_id}",
                    metadata={"method": i.inspection_method, "severity": i.severity, "model": i.model_name}
                )
            )

        # 3. Defect Records
        defects = db.query(DefectRecord).filter(DefectRecord.asset_id == asset_id).all()
        for d in defects:
            events.append(
                TimelineEvent(
                    event_id=f"evt-defect-{d.defect_id}",
                    asset_id=asset_id,
                    component_id=d.component_id,
                    event_type="DEFECT_DETECTED",
                    timestamp=d.detection_timestamp.replace(tzinfo=timezone.utc) if d.detection_timestamp.tzinfo is None else d.detection_timestamp,
                    title=f"Defect Detected: {d.defect_type.upper()}",
                    description=f"Confidence: {d.confidence*100:.1f}%, Affected Area: {d.affected_area_percentage or 0:.2f}%, Crack Length: {d.crack_length_pixels or 0:.1f}px",
                    source_reference=f"defect_records/{d.defect_id}",
                    metadata={"defect_type": d.defect_type, "confidence": d.confidence}
                )
            )

        # 4. Work Order Events
        wos = db.query(WorkOrder).filter(WorkOrder.component_id.in_(comp_ids)).all()
        for w in wos:
            events.append(
                TimelineEvent(
                    event_id=f"evt-wo-{w.work_order_id}",
                    asset_id=asset_id,
                    component_id=w.component_id,
                    event_type="WORK_ORDER_CREATED",
                    timestamp=w.created_at.replace(tzinfo=timezone.utc) if w.created_at.tzinfo is None else w.created_at,
                    title=f"Work Order {w.work_order_id} ({w.status})",
                    description=f"Action: {w.recommended_action}",
                    source_reference=f"work_orders/{w.work_order_id}",
                    metadata={"priority": w.priority, "status": w.status, "cost": w.actual_cost or w.estimated_cost}
                )
            )

        # 5. Inspection Review Audit Trail
        reviews = db.query(InspectionReview).filter(InspectionReview.component_id.in_(comp_ids)).all()
        for r in reviews:
            for audit in r.audit_logs:
                events.append(
                    TimelineEvent(
                        event_id=f"evt-audit-{audit.audit_id}",
                        asset_id=asset_id,
                        component_id=r.component_id,
                        event_type=audit.event_type,
                        timestamp=audit.created_at.replace(tzinfo=timezone.utc) if audit.created_at.tzinfo is None else audit.created_at,
                        title=f"Review Action: {audit.event_type.replace('_', ' ')}",
                        description=f"{audit.change_summary or 'Status transition'}" + (f" by {audit.reviewer_name}" if audit.reviewer_name else ""),
                        source_reference=f"review_audit_logs/{audit.audit_id}",
                        metadata={"new_status": audit.new_status, "reviewer_id": audit.reviewer_id}
                    )
                )

        # 6. Incidents
        if comp_types:
            incidents = db.query(IncidentRecord).filter(IncidentRecord.component_type.in_(comp_types)).all()
            for inc in incidents:
                events.append(
                    TimelineEvent(
                        event_id=f"evt-inc-{inc.incident_id}",
                        asset_id=asset_id,
                        component_id=None,
                        event_type="INCIDENT",
                        timestamp=inc.occurred_at.replace(tzinfo=timezone.utc) if inc.occurred_at.tzinfo is None else inc.occurred_at,
                        title=f"Incident Record: {inc.incident_id} ({inc.severity})",
                        description=f"{inc.description} Root cause: {inc.root_cause}",
                        source_reference=f"incident_records/{inc.incident_id}",
                        metadata={"severity": inc.severity, "root_cause": inc.root_cause}
                    )
                )

        # Sort descending by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        return AssetTimelineResponse(
            asset_id=asset_id,
            events_count=len(sorted_events),
            events=sorted_events
        )


# Global service instance
timeline_service = TimelineService()
