"""Deterministic trend calculation service for historical defect metrics (Phase 3A)."""

from datetime import datetime
from typing import Dict, List
from sqlalchemy import desc
from sqlalchemy.orm import Session
from backend.app.database.models.defect import DefectRecord
from backend.app.database.models.inspection import InspectionRecord
from backend.app.schemas.analytics import DefectTrendAnalysis, DefectTrendPoint
from backend.app.services.analytics.history_service import history_service


class TrendService:
    """Computes mathematical trend slopes and historical metrics across inspection series."""

    def calculate_asset_trends(self, db: Session, asset_id: str) -> DefectTrendAnalysis:
        defects = (
            db.query(DefectRecord)
            .filter(DefectRecord.asset_id == asset_id)
            .order_by(DefectRecord.detection_timestamp)
            .all()
        )

        inspections = history_service.get_asset_inspections(db, asset_id, limit=200)
        # Sort ascending
        inspections = sorted(inspections, key=lambda i: i.inspection_timestamp)

        if not inspections:
            return DefectTrendAnalysis(
                asset_id=asset_id,
                total_inspections=0,
                total_defects_detected=0,
                average_defects_per_inspection=0.0,
                defect_count_trend="INSUFFICIENT_DATA",
                area_severity_trend="STABLE",
                average_confidence=0.0,
                average_days_between_inspections=None,
                recurring_defect_types=[],
                time_series=[]
            )

        # Build time series grouping by inspection
        time_series: List[DefectTrendPoint] = []
        insp_defect_map: Dict[str, List[DefectRecord]] = {}
        for d in defects:
            insp_defect_map.setdefault(d.inspection_id, []).append(d)

        for insp in inspections:
            cur_defects = insp_defect_map.get(insp.inspection_id, [])
            count = len(cur_defects)
            max_area = max([d.affected_area_percentage or 0.0 for d in cur_defects], default=0.0)
            total_crack_len = sum([d.crack_length_pixels or 0.0 for d in cur_defects])
            avg_conf = sum([d.confidence for d in cur_defects]) / count if count > 0 else 0.0

            time_series.append(
                DefectTrendPoint(
                    timestamp=insp.inspection_timestamp,
                    inspection_id=insp.inspection_id,
                    defect_count=count,
                    max_affected_area_percentage=round(max_area, 2),
                    total_crack_length_pixels=round(total_crack_len, 1),
                    avg_confidence=round(avg_conf, 3),
                    priority=insp.severity
                )
            )

        # Defect count slope analysis
        total_defects = len(defects)
        avg_defects_per_insp = total_defects / len(inspections) if len(inspections) > 0 else 0.0

        if len(time_series) >= 2:
            first_half = time_series[:len(time_series)//2]
            second_half = time_series[len(time_series)//2:]
            avg_first = sum(p.defect_count for p in first_half) / len(first_half)
            avg_second = sum(p.defect_count for p in second_half) / len(second_half)

            if avg_second > avg_first * 1.2:
                defect_trend = "INCREASING"
            elif avg_second < avg_first * 0.8:
                defect_trend = "DECREASING"
            else:
                defect_trend = "STABLE"

            # Area trend
            area_first = sum(p.max_affected_area_percentage for p in first_half) / len(first_half)
            area_second = sum(p.max_affected_area_percentage for p in second_half) / len(second_half)
            if area_second > area_first * 1.15:
                area_trend = "EXPANDING"
            elif area_second == 0.0 and area_first > 0.0:
                area_trend = "RESOLVED"
            else:
                area_trend = "STABLE"
        else:
            defect_trend = "STABLE" if total_defects > 0 else "INSUFFICIENT_DATA"
            area_trend = "STABLE"

        # Time between inspections
        intervals = []
        for i in range(1, len(inspections)):
            delta = (inspections[i].inspection_timestamp - inspections[i-1].inspection_timestamp).total_seconds() / 86400.0
            if delta > 0:
                intervals.append(delta)
        avg_days = round(sum(intervals) / len(intervals), 1) if intervals else None

        # Recurring defect types
        defect_type_counts: Dict[str, int] = {}
        for d in defects:
            defect_type_counts[d.defect_type] = defect_type_counts.get(d.defect_type, 0) + 1
        recurring = [dtype for dtype, count in defect_type_counts.items() if count >= 2]

        all_conf = [d.confidence for d in defects]
        avg_conf_overall = round(sum(all_conf) / len(all_conf), 3) if all_conf else 0.0

        return DefectTrendAnalysis(
            asset_id=asset_id,
            total_inspections=len(inspections),
            total_defects_detected=total_defects,
            average_defects_per_inspection=round(avg_defects_per_insp, 2),
            defect_count_trend=defect_trend,
            area_severity_trend=area_trend,
            average_confidence=avg_conf_overall,
            average_days_between_inspections=avg_days,
            recurring_defect_types=recurring,
            time_series=time_series
        )


# Global service instance
trend_service = TrendService()
