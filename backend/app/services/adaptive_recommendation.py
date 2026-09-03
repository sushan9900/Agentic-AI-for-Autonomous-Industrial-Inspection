"""Adaptive Recommendation Engine (Phase 7E)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session

from backend.app.schemas.adaptive_recommendation import (
    AdaptiveRecommendation,
    AdaptiveRecommendationsResponse,
)
from backend.app.services.inspection_learning import inspection_learning_service


class AdaptiveRecommendationService:
    """
    Deterministic advisory recommendation service synthesized from human review learning.
    Translates detected error patterns into non-authoritative engineering advisories.
    """

    def generate_recommendations(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None
    ) -> List[AdaptiveRecommendation]:
        """
        Generates explainable, deterministic advisory recommendations based on active error patterns.
        Strictly advisory: authoritative = False.
        """
        patterns = inspection_learning_service.detect_error_patterns(
            db=db,
            asset_id=asset_id,
            component_id=component_id
        )

        recommendations: List[AdaptiveRecommendation] = []
        now = datetime.now(timezone.utc)

        for p in patterns:
            if p.pattern_type == "REPEATED_FALSE_NEGATIVES":
                rec_id = f"rec-fn-{p.asset_id or 'all'}-{p.component_id or 'all'}"
                comp_str = f" on component '{p.component_id}'" if p.component_id else ""
                recommendations.append(
                    AdaptiveRecommendation(
                        recommendation_id=rec_id,
                        asset_id=p.asset_id,
                        component_id=p.component_id,
                        recommendation_type="HIGHER_REVIEW_PRIORITY",
                        reason=(
                            f"Detected {p.occurrence_count} confirmed missed defects (false negatives) on "
                            f"asset '{p.asset_id}'{comp_str}. Priority review elevation advised."
                        ),
                        supporting_pattern_ids=[p.pattern_id],
                        supporting_inspection_ids=p.affected_inspection_ids,
                        advisory_priority="CRITICAL",
                        suggested_score_adjustment=15,
                        created_at=now,
                        authoritative=False
                    )
                )

            elif p.pattern_type == "RECURRING_SEVERITY_UNDERESTIMATION":
                rec_id = f"rec-under-{p.asset_id or 'all'}-{p.component_id or 'all'}"
                comp_str = f" on component '{p.component_id}'" if p.component_id else ""
                recommendations.append(
                    AdaptiveRecommendation(
                        recommendation_id=rec_id,
                        asset_id=p.asset_id,
                        component_id=p.component_id,
                        recommendation_type="HIGHER_REVIEW_PRIORITY",
                        reason=(
                            f"Detected {p.occurrence_count} AI severity underestimations on "
                            f"asset '{p.asset_id}'{comp_str}. Human review queue elevation advised."
                        ),
                        supporting_pattern_ids=[p.pattern_id],
                        supporting_inspection_ids=p.affected_inspection_ids,
                        advisory_priority="HIGH",
                        suggested_score_adjustment=10,
                        created_at=now,
                        authoritative=False
                    )
                )

            elif p.pattern_type == "REPEATED_FALSE_POSITIVES":
                rec_id = f"rec-fp-{p.asset_id or 'all'}-{p.component_id or 'all'}"
                comp_str = f" on component '{p.component_id}'" if p.component_id else ""
                recommendations.append(
                    AdaptiveRecommendation(
                        recommendation_id=rec_id,
                        asset_id=p.asset_id,
                        component_id=p.component_id,
                        recommendation_type="REQUEST_ADDITIONAL_EVIDENCE",
                        reason=(
                            f"Detected {p.occurrence_count} recurring false positive defect detections on "
                            f"asset '{p.asset_id}'{comp_str}. Multi-angle visual evidence or NDE verification recommended."
                        ),
                        supporting_pattern_ids=[p.pattern_id],
                        supporting_inspection_ids=p.affected_inspection_ids,
                        advisory_priority="MEDIUM",
                        suggested_score_adjustment=0,
                        created_at=now,
                        authoritative=False
                    )
                )

            elif p.pattern_type == "REPEATED_ACTION_DISAGREEMENT":
                rec_id = f"rec-act-{p.asset_id or 'all'}-{p.component_id or 'all'}"
                comp_str = f" on component '{p.component_id}'" if p.component_id else ""
                recommendations.append(
                    AdaptiveRecommendation(
                        recommendation_id=rec_id,
                        asset_id=p.asset_id,
                        component_id=p.component_id,
                        recommendation_type="REQUIRE_EXPERT_REVIEW",
                        reason=(
                            f"Detected {p.occurrence_count} operational action disagreements on "
                            f"asset '{p.asset_id}'{comp_str}. Senior specialist inspection signoff advised."
                        ),
                        supporting_pattern_ids=[p.pattern_id],
                        supporting_inspection_ids=p.affected_inspection_ids,
                        advisory_priority="HIGH",
                        suggested_score_adjustment=5,
                        created_at=now,
                        authoritative=False
                    )
                )

            elif p.pattern_type == "RECURRING_SEVERITY_OVERESTIMATION":
                rec_id = f"rec-over-{p.asset_id or 'all'}-{p.component_id or 'all'}"
                comp_str = f" on component '{p.component_id}'" if p.component_id else ""
                recommendations.append(
                    AdaptiveRecommendation(
                        recommendation_id=rec_id,
                        asset_id=p.asset_id,
                        component_id=p.component_id,
                        recommendation_type="REQUEST_ADDITIONAL_EVIDENCE",
                        reason=(
                            f"Detected {p.occurrence_count} recurring severity overestimations on "
                            f"asset '{p.asset_id}'{comp_str}. Physical dimensional confirmation advised."
                        ),
                        supporting_pattern_ids=[p.pattern_id],
                        supporting_inspection_ids=p.affected_inspection_ids,
                        advisory_priority="LOW",
                        suggested_score_adjustment=-5,
                        created_at=now,
                        authoritative=False
                    )
                )

        return recommendations

    def get_recommendations_response(
        self,
        db: Session,
        asset_id: Optional[str] = None,
        component_id: Optional[str] = None
    ) -> AdaptiveRecommendationsResponse:
        """Packages active recommendations in response envelope."""
        recs = self.generate_recommendations(db, asset_id, component_id)
        return AdaptiveRecommendationsResponse(
            total_recommendations=len(recs),
            recommendations=recs
        )


adaptive_recommendation_service = AdaptiveRecommendationService()
