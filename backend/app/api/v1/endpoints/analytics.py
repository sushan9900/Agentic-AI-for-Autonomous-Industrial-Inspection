"""FastAPI REST endpoints for fleet-wide inspection analytics, defect summaries, and risk overview (Phase 3A)."""

from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from backend.app.database.models.asset import Asset
from backend.app.database.models.defect import DefectRecord
from backend.app.database.models.inspection import InspectionRecord
from backend.app.database.models.review import InspectionReview
from backend.app.database.models.work_order import WorkOrder
from backend.app.database.session import get_db
from backend.app.schemas.analytics import (
    AnalyticsOverviewResponse,
    DefectAnalyticsResponse,
    RiskAnalyticsResponse,
)
from backend.app.services.analytics import asset_service, risk_service

router = APIRouter()


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fleet Analytics Overview",
    description="Calculates fleet-wide metrics: asset counts, total inspections, defect frequency, open reviews, and risk band totals.",
    tags=["Fleet Analytics"]
)
def get_analytics_overview(db: Session = Depends(get_db)) -> AnalyticsOverviewResponse:
    total_assets = db.query(func.count(Asset.id)).scalar() or 0
    total_inspections = db.query(func.count(InspectionRecord.id)).scalar() or 0
    total_defects = db.query(func.count(DefectRecord.id)).scalar() or 0
    open_reviews = db.query(func.count(InspectionReview.review_id)).filter(
        InspectionReview.status.in_(["PENDING_HUMAN_REVIEW", "IN_REVIEW", "REVISION_REQUESTED"])
    ).scalar() or 0
    approved_wos = db.query(func.count(InspectionReview.review_id)).filter(
        InspectionReview.status == "APPROVED"
    ).scalar() or 0

    # Calculate risk bands across assets
    assets = db.query(Asset.asset_id).all()
    high_risk_count = 0
    critical_risk_count = 0
    for (a_id,) in assets:
        risk = risk_service.calculate_asset_risk(db, a_id)
        if risk.risk_band == "CRITICAL":
            critical_risk_count += 1
        elif risk.risk_band == "HIGH":
            high_risk_count += 1

    # Recent inspections
    recent_insps = (
        db.query(InspectionRecord)
        .order_by(desc(InspectionRecord.inspection_timestamp))
        .limit(5)
        .all()
    )
    recent_list = [
        {
            "inspection_id": i.inspection_id,
            "component_id": i.component_id,
            "timestamp": i.inspection_timestamp.isoformat(),
            "method": i.inspection_method,
            "severity": i.severity,
            "defect_type": i.defect_type,
            "confidence": i.confidence
        }
        for i in recent_insps
    ]

    return AnalyticsOverviewResponse(
        total_assets=total_assets,
        total_inspections=total_inspections,
        total_detected_defects=total_defects,
        open_reviews_count=open_reviews,
        approved_work_orders_count=approved_wos,
        high_risk_assets_count=high_risk_count,
        critical_risk_assets_count=critical_risk_count,
        recent_inspections=recent_list
    )


@router.get(
    "/analytics/defects",
    response_model=DefectAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fleet Defect Analytics",
    description="Aggregates defect distributions, average detection confidence by defect type, and top affected assets.",
    tags=["Fleet Analytics"]
)
def get_defect_analytics(db: Session = Depends(get_db)) -> DefectAnalyticsResponse:
    total_defects = db.query(func.count(DefectRecord.id)).scalar() or 0

    # Group by defect type
    type_counts = (
        db.query(DefectRecord.defect_type, func.count(DefectRecord.id))
        .group_by(DefectRecord.defect_type)
        .all()
    )
    defects_by_type = {dtype: count for dtype, count in type_counts}

    # Avg confidence by type
    type_conf = (
        db.query(DefectRecord.defect_type, func.avg(DefectRecord.confidence))
        .group_by(DefectRecord.defect_type)
        .all()
    )
    avg_conf_by_type = {dtype: round(float(avg_c), 3) for dtype, avg_c in type_conf if avg_c is not None}

    # Top affected assets
    asset_defect_counts = (
        db.query(DefectRecord.asset_id, func.count(DefectRecord.id))
        .group_by(DefectRecord.asset_id)
        .order_by(desc(func.count(DefectRecord.id)))
        .limit(5)
        .all()
    )
    top_affected = [{"asset_id": aid, "defect_count": count} for aid, count in asset_defect_counts]

    return DefectAnalyticsResponse(
        total_defects=total_defects,
        defects_by_type=defects_by_type,
        avg_confidence_by_type=avg_conf_by_type,
        top_affected_assets=top_affected
    )


@router.get(
    "/analytics/risk",
    response_model=RiskAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fleet Risk Distribution",
    description="Provides risk-band distributions (CRITICAL, HIGH, MEDIUM, LOW), average fleet risk, and prioritized high-risk asset list.",
    tags=["Fleet Analytics"]
)
def get_risk_analytics(db: Session = Depends(get_db)) -> RiskAnalyticsResponse:
    assets = db.query(Asset).all()
    risk_distribution = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    high_risk_list = []
    total_score = 0

    for a in assets:
        risk = risk_service.calculate_asset_risk(db, a.asset_id)
        risk_distribution[risk.risk_band] = risk_distribution.get(risk.risk_band, 0) + 1
        total_score += risk.risk_score

        if risk.risk_band in ("CRITICAL", "HIGH"):
            high_risk_list.append({
                "asset_id": a.asset_id,
                "name": a.name,
                "asset_type": a.asset_type,
                "location": a.location,
                "risk_score": risk.risk_score,
                "risk_band": risk.risk_band,
                "contributing_factors": risk.contributing_factors
            })

    # Sort high risk list descending
    high_risk_list.sort(key=lambda x: x["risk_score"], reverse=True)
    avg_score = round(total_score / len(assets), 1) if assets else 0.0

    return RiskAnalyticsResponse(
        risk_band_distribution=risk_distribution,
        high_risk_assets=high_risk_list,
        average_fleet_risk_score=avg_score
    )
