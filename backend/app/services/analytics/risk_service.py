"""Deterministic and explainable asset operational risk calculation service (Phase 3A)."""

from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session
from backend.app.database.models.defect import DefectRecord
from backend.app.database.models.work_order import WorkOrder
from backend.app.schemas.analytics import AssetRiskSnapshot
from backend.app.services.analytics.history_service import history_service


class RiskService:
    """Calculates explainable operational risk indicators based on historical inspection and work-order data."""

    def calculate_asset_risk(self, db: Session, asset_id: str) -> AssetRiskSnapshot:
        factors: List[str] = []
        evidence_ids: List[str] = []
        score = 10  # Base operational baseline

        # 1. Inspection Recency
        latest_insp = history_service.get_latest_inspection(db, asset_id)
        days_since_insp = None
        if latest_insp:
            evidence_ids.append(latest_insp.inspection_id)
            delta = (datetime.now(timezone.utc) - latest_insp.inspection_timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 86400.0
            days_since_insp = int(delta)
            if days_since_insp > 365:
                score += 20
                factors.append(f"Inspection significantly overdue ({days_since_insp} days since last inspection, exceeding 365-day survey threshold).")
            elif days_since_insp > 180:
                score += 10
                factors.append(f"Routine inspection interval exceeded ({days_since_insp} days elapsed).")
        else:
            score += 25
            factors.append("Asset has no baseline inspection records logged.")

        # 2. Defect History & Recurrence
        defects = history_service.get_asset_defects(db, asset_id)
        total_defects = len(defects)
        if total_defects > 0:
            score += min(total_defects * 5, 25)
            factors.append(f"{total_defects} physical defect(s) detected across inspection history.")

            # Recurrence check
            inspections_with_defects = {d.inspection_id for d in defects}
            if len(inspections_with_defects) >= 2:
                score += 20
                factors.append(f"Defect recurrence observed across {len(inspections_with_defects)} distinct inspection transactions.")

            # Severity metrics
            max_area = max([d.affected_area_percentage or 0.0 for d in defects], default=0.0)
            if max_area >= 4.0:
                score += 15
                factors.append(f"High localized surface affected area detected ({max_area:.2f}% frame area).")
            elif max_area >= 2.0:
                score += 8
                factors.append(f"Moderate surface affected area detected ({max_area:.2f}%).")

            max_crack = max([d.crack_length_pixels or 0.0 for d in defects], default=0.0)
            if max_crack >= 200.0:
                score += 10
                factors.append(f"Significant linear crack length detected ({max_crack:.1f}px).")

        # 3. Open Unresolved Work Orders
        work_orders = history_service.get_asset_work_orders(db, asset_id)
        open_wos = [w for w in work_orders if w.status not in ("COMPLETED", "CLOSED", "REJECTED")]
        if open_wos:
            critical_open = any(w.priority == "CRITICAL" for w in open_wos)
            if critical_open:
                score += 25
                factors.append(f"{len(open_wos)} unresolved maintenance work order(s) pending, including CRITICAL priority orders.")
            else:
                score += 15
                factors.append(f"{len(open_wos)} open maintenance work order(s) awaiting execution.")

        # Clamp score [0, 100]
        final_score = min(max(score, 0), 100)

        # Risk Band Assignment
        if final_score >= 75:
            risk_band = "CRITICAL"
        elif final_score >= 50:
            risk_band = "HIGH"
        elif final_score >= 25:
            risk_band = "MEDIUM"
        else:
            risk_band = "LOW"

        if not factors:
            factors.append("Asset operates within normal operational baseline parameters with no active defect triggers.")

        return AssetRiskSnapshot(
            asset_id=asset_id,
            risk_score=final_score,
            risk_band=risk_band,
            contributing_factors=factors,
            evidence_inspection_ids=list(set(evidence_ids)),
            unresolved_work_orders_count=len(open_wos),
            recurring_defects_count=total_defects,
            days_since_last_inspection=days_since_insp,
            calculation_timestamp=datetime.now(timezone.utc)
        )


# Global service instance
risk_service = RiskService()
