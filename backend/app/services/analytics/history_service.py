"""Historical inspection and defect data access service (Phase 3A)."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session
from backend.app.database.models.asset import Asset
from backend.app.database.models.component import Component
from backend.app.database.models.defect import DefectRecord
from backend.app.database.models.inspection import InspectionRecord
from backend.app.database.models.review import InspectionReview
from backend.app.database.models.work_order import WorkOrder
from backend.app.schemas.analytics import DefectRecordRead
from backend.app.schemas.inspection_record import InspectionRecordRead
from backend.app.schemas.work_order import WorkOrderRead


class HistoryService:
    """Retrieval service for historical inspections, defects, and approved work orders."""

    @staticmethod
    def _get_asset_component_ids(db: Session, asset_id: str) -> List[str]:
        components = db.query(Component.component_id).filter(Component.asset_id == asset_id).all()
        return [c[0] for c in components]

    def get_asset_inspections(
        self,
        db: Session,
        asset_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InspectionRecordRead]:
        comp_ids = self._get_asset_component_ids(db, asset_id)
        if not comp_ids:
            return []

        query = db.query(InspectionRecord).filter(InspectionRecord.component_id.in_(comp_ids))
        if start_date:
            query = query.filter(InspectionRecord.inspection_timestamp >= start_date)
        if end_date:
            query = query.filter(InspectionRecord.inspection_timestamp <= end_date)

        records = query.order_by(desc(InspectionRecord.inspection_timestamp)).offset(skip).limit(limit).all()
        return [InspectionRecordRead.model_validate(r) for r in records]

    def get_latest_inspection(self, db: Session, asset_id: str) -> Optional[InspectionRecordRead]:
        comp_ids = self._get_asset_component_ids(db, asset_id)
        if not comp_ids:
            return None

        record = (
            db.query(InspectionRecord)
            .filter(InspectionRecord.component_id.in_(comp_ids))
            .order_by(desc(InspectionRecord.inspection_timestamp))
            .first()
        )
        return InspectionRecordRead.model_validate(record) if record else None

    def get_previous_inspection(self, db: Session, asset_id: str) -> Optional[InspectionRecordRead]:
        comp_ids = self._get_asset_component_ids(db, asset_id)
        if not comp_ids:
            return None

        records = (
            db.query(InspectionRecord)
            .filter(InspectionRecord.component_id.in_(comp_ids))
            .order_by(desc(InspectionRecord.inspection_timestamp))
            .limit(2)
            .all()
        )
        return InspectionRecordRead.model_validate(records[1]) if len(records) > 1 else None

    def get_asset_defects(
        self,
        db: Session,
        asset_id: str,
        defect_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DefectRecordRead]:
        query = db.query(DefectRecord).filter(DefectRecord.asset_id == asset_id)
        if defect_type:
            query = query.filter(DefectRecord.defect_type == defect_type.lower())

        records = query.order_by(desc(DefectRecord.detection_timestamp)).offset(skip).limit(limit).all()
        return [DefectRecordRead.model_validate(r) for r in records]

    def get_asset_work_orders(
        self,
        db: Session,
        asset_id: str,
        status: Optional[str] = None
    ) -> List[WorkOrderRead]:
        comp_ids = self._get_asset_component_ids(db, asset_id)
        if not comp_ids:
            return []

        query = db.query(WorkOrder).filter(WorkOrder.component_id.in_(comp_ids))
        if status:
            query = query.filter(WorkOrder.status == status.upper())

        orders = query.order_by(desc(WorkOrder.created_at)).all()
        return [WorkOrderRead.model_validate(w) for w in orders]


# Global service instance
history_service = HistoryService()
