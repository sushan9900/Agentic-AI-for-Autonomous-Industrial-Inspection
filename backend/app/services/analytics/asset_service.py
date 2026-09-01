"""Service layer for asset management, queries, and summaries (Phase 3A)."""

from typing import List, Optional
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models.asset import Asset
from backend.app.database.models.component import Component
from backend.app.database.models.defect import DefectRecord
from backend.app.database.models.inspection import InspectionRecord
from backend.app.database.models.review import InspectionReview
from backend.app.database.models.work_order import WorkOrder
from backend.app.schemas.asset import AssetCreate, AssetDetailRead, AssetSummaryRead, AssetUpdate


class AssetNotFoundError(Exception):
    """Exception raised when an asset is not found."""
    pass


class AssetService:
    """Business logic for physical asset registry."""

    def get_asset(self, db: Session, asset_id: str) -> Asset:
        asset = (
            db.query(Asset)
            .options(joinedload(Asset.components))
            .filter(Asset.asset_id == asset_id)
            .first()
        )
        if not asset:
            raise AssetNotFoundError(f"Asset '{asset_id}' was not found.")
        return asset

    def get_asset_detail(self, db: Session, asset_id: str) -> AssetDetailRead:
        asset = self.get_asset(db, asset_id)
        
        # Calculate counts
        defects_count = db.query(func.count(DefectRecord.id)).filter(DefectRecord.asset_id == asset_id).scalar() or 0
        comp_ids = [c.component_id for c in asset.components]
        inspections_count = db.query(func.count(InspectionRecord.id)).filter(InspectionRecord.component_id.in_(comp_ids)).scalar() or 0
        open_wo_count = db.query(func.count(WorkOrder.id)).filter(WorkOrder.component_id.in_(comp_ids), WorkOrder.status != "COMPLETED").scalar() or 0

        # Lazy import to avoid circular dependency
        from backend.app.services.analytics.risk_service import risk_service
        risk_snap = risk_service.calculate_asset_risk(db, asset_id)

        return AssetDetailRead(
            id=asset.id,
            asset_id=asset.asset_id,
            asset_code=asset.asset_code,
            asset_type=asset.asset_type,
            name=asset.name,
            manufacturer=asset.manufacturer,
            model=asset.model,
            serial_number=asset.serial_number,
            installation_date=asset.installation_date,
            location=asset.location,
            operational_status=asset.operational_status,
            warranty_start=asset.warranty_start,
            warranty_end=asset.warranty_end,
            source_type=asset.source_type,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            components=asset.components,
            total_defects_count=defects_count,
            total_inspections_count=inspections_count,
            open_work_orders_count=open_wo_count,
            current_risk_score=risk_snap.risk_score,
            current_risk_band=risk_snap.risk_band
        )

    def list_assets(
        self,
        db: Session,
        asset_type: Optional[str] = None,
        operational_status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AssetSummaryRead]:
        query = db.query(Asset)

        if asset_type:
            query = query.filter(Asset.asset_type == asset_type.upper())
        if operational_status:
            query = query.filter(Asset.operational_status == operational_status.upper())
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Asset.asset_id.ilike(search_term),
                    Asset.name.ilike(search_term),
                    Asset.location.ilike(search_term)
                )
            )

        assets = query.order_by(Asset.asset_id).offset(skip).limit(limit).all()

        from backend.app.services.analytics.risk_service import risk_service

        summaries = []
        for a in assets:
            comp_ids = [c.component_id for c in a.components]
            defects_count = db.query(func.count(DefectRecord.id)).filter(DefectRecord.asset_id == a.asset_id).scalar() or 0
            
            # Latest inspection date
            last_insp = (
                db.query(InspectionRecord.inspection_timestamp)
                .filter(InspectionRecord.component_id.in_(comp_ids))
                .order_by(desc(InspectionRecord.inspection_timestamp))
                .first()
            )
            last_date = last_insp[0] if last_insp else None

            # Open work orders
            open_wo = db.query(func.count(WorkOrder.id)).filter(
                WorkOrder.component_id.in_(comp_ids),
                WorkOrder.status != "COMPLETED"
            ).scalar() or 0

            # Risk calculation
            risk = risk_service.calculate_asset_risk(db, a.asset_id)

            summaries.append(
                AssetSummaryRead(
                    asset_id=a.asset_id,
                    asset_code=a.asset_code,
                    name=a.name,
                    asset_type=a.asset_type,
                    location=a.location,
                    operational_status=a.operational_status,
                    last_inspection_date=last_date,
                    total_defects_count=defects_count,
                    open_work_orders_count=open_wo,
                    current_risk_score=risk.risk_score,
                    current_risk_band=risk.risk_band
                )
            )
        return summaries

    def create_asset(self, db: Session, payload: AssetCreate) -> Asset:
        existing = db.query(Asset).filter(Asset.asset_id == payload.asset_id).first()
        if existing:
            raise ValueError(f"Asset with ID '{payload.asset_id}' already exists.")

        asset = Asset(**payload.model_dump())
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    def update_asset(self, db: Session, asset_id: str, payload: AssetUpdate) -> Asset:
        asset = self.get_asset(db, asset_id)
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(asset, key, value)

        db.commit()
        db.refresh(asset)
        return asset


# Global service instance
asset_service = AssetService()
