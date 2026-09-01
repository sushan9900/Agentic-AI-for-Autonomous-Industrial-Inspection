"""FastAPI REST endpoints for asset management, historical inspections, defect tracking, risk, and timelines (Phase 3A)."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.analytics import (
    AssetRiskSnapshot,
    AssetTimelineResponse,
    DefectRecordRead,
    DefectTrendAnalysis,
)
from backend.app.schemas.asset import (
    AssetCreate,
    AssetDetailRead,
    AssetRead,
    AssetSummaryRead,
    AssetUpdate,
)
from backend.app.schemas.inspection_record import InspectionRecordRead
from backend.app.schemas.work_order import WorkOrderRead
from backend.app.services.analytics import (
    AssetNotFoundError,
    asset_service,
    history_service,
    risk_service,
    timeline_service,
    trend_service,
)

router = APIRouter()


@router.get(
    "/assets",
    response_model=List[AssetSummaryRead],
    status_code=status.HTTP_200_OK,
    summary="List Industrial Assets",
    description="Retrieves a list of industrial assets with risk indicators, inspection recency, and defect counts.",
    tags=["Asset Management"]
)
def list_assets(
    asset_type: Optional[str] = Query(default=None),
    operational_status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> List[AssetSummaryRead]:
    return asset_service.list_assets(
        db=db,
        asset_type=asset_type,
        operational_status=operational_status,
        search=search,
        skip=skip,
        limit=limit
    )


@router.post(
    "/assets",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Industrial Asset",
    description="Registers a new physical industrial asset in the asset database.",
    tags=["Asset Management"]
)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db)
) -> AssetRead:
    try:
        return asset_service.create_asset(db=db, payload=payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/assets/{asset_id}",
    response_model=AssetDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Get Asset Details",
    description="Retrieves comprehensive asset specifications, components, inspection metrics, and risk overview.",
    tags=["Asset Management"]
)
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db)
) -> AssetDetailRead:
    try:
        return asset_service.get_asset_detail(db=db, asset_id=asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/assets/{asset_id}",
    response_model=AssetRead,
    status_code=status.HTTP_200_OK,
    summary="Update Asset Properties",
    description="Updates operational metadata or physical parameters of an industrial asset.",
    tags=["Asset Management"]
)
def update_asset(
    asset_id: str,
    payload: AssetUpdate,
    db: Session = Depends(get_db)
) -> AssetRead:
    try:
        return asset_service.update_asset(db=db, asset_id=asset_id, payload=payload)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/assets/{asset_id}/inspections",
    response_model=List[InspectionRecordRead],
    status_code=status.HTTP_200_OK,
    summary="Get Asset Inspection History",
    description="Retrieves chronological inspection records for all components on the target asset.",
    tags=["Asset Intelligence"]
)
def get_asset_inspections(
    asset_id: str,
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> List[InspectionRecordRead]:
    try:
        asset_service.get_asset(db, asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return history_service.get_asset_inspections(
        db=db,
        asset_id=asset_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )


@router.get(
    "/assets/{asset_id}/defects",
    response_model=List[DefectRecordRead],
    status_code=status.HTTP_200_OK,
    summary="Get Asset Defect History",
    description="Retrieves normalized historical defect records detected across inspections for this asset.",
    tags=["Asset Intelligence"]
)
def get_asset_defects(
    asset_id: str,
    defect_type: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db)
) -> List[DefectRecordRead]:
    try:
        asset_service.get_asset(db, asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return history_service.get_asset_defects(
        db=db,
        asset_id=asset_id,
        defect_type=defect_type,
        skip=skip,
        limit=limit
    )


@router.get(
    "/assets/{asset_id}/risk",
    response_model=AssetRiskSnapshot,
    status_code=status.HTTP_200_OK,
    summary="Get Asset Operational Risk Snapshot",
    description="Calculates a deterministic and explainable operational risk indicator with contributing factor breakdown.",
    tags=["Asset Intelligence"]
)
def get_asset_risk(
    asset_id: str,
    db: Session = Depends(get_db)
) -> AssetRiskSnapshot:
    try:
        asset_service.get_asset(db, asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return risk_service.calculate_asset_risk(db=db, asset_id=asset_id)


@router.get(
    "/assets/{asset_id}/trends",
    response_model=DefectTrendAnalysis,
    status_code=status.HTTP_200_OK,
    summary="Get Asset Defect Trend Analysis",
    description="Calculates mathematical time-series trends for defect counts, affected surface areas, and inspection intervals.",
    tags=["Asset Intelligence"]
)
def get_asset_trends(
    asset_id: str,
    db: Session = Depends(get_db)
) -> DefectTrendAnalysis:
    try:
        asset_service.get_asset(db, asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return trend_service.calculate_asset_trends(db=db, asset_id=asset_id)


@router.get(
    "/assets/{asset_id}/work-orders",
    response_model=List[WorkOrderRead],
    status_code=status.HTTP_200_OK,
    summary="Get Asset Work Orders",
    description="Retrieves all maintenance work orders associated with the asset components.",
    tags=["Asset Intelligence"]
)
def get_asset_work_orders(
    asset_id: str,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db)
) -> List[WorkOrderRead]:
    try:
        asset_service.get_asset(db, asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return history_service.get_asset_work_orders(db=db, asset_id=asset_id, status=status_filter)


@router.get(
    "/assets/{asset_id}/timeline",
    response_model=AssetTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Unified Asset Chronological Timeline",
    description="Aggregates inspections, defects, reviews, work orders, maintenance, and incident history into a single timeline.",
    tags=["Asset Intelligence"]
)
def get_asset_timeline(
    asset_id: str,
    db: Session = Depends(get_db)
) -> AssetTimelineResponse:
    try:
        asset_service.get_asset(db, asset_id)
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return timeline_service.build_asset_timeline(db=db, asset_id=asset_id)
