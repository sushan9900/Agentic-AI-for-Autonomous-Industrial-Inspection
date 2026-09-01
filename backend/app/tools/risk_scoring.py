"""Agent tool for deterministic and explainable operational risk calculation (Phase 3B)."""

from typing import List, Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from backend.app.tools.base import BaseAgentTool


class RiskScoreInput(BaseModel):
    """Input parameters for calculate_risk_score tool."""
    defect_count: int = Field(default=0, ge=0, description="Total detected defect count")
    max_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Maximum detection confidence")
    max_affected_area_percentage: float = Field(default=0.0, ge=0.0, description="Max localized surface affected area percentage")
    max_crack_length_pixels: float = Field(default=0.0, ge=0.0, description="Max linear crack length in pixels")
    service_age_years: Optional[float] = Field(default=None, description="Asset operational age in years")
    has_active_warranty: bool = Field(default=False, description="Whether asset is under active manufacturer warranty")
    recurrence_count: int = Field(default=0, ge=0, description="Number of previous inspections detecting similar defects")
    similar_incident_max_severity: Optional[str] = Field(default=None, description="Max severity of matching historical failure incidents")
    component_criticality: str = Field(default="MEDIUM", description="Component operational criticality (CRITICAL, HIGH, MEDIUM, LOW)")

    model_config = ConfigDict(extra="forbid")


class RiskScoreOutput(BaseModel):
    """Structured output for calculate_risk_score tool."""
    risk_score: int = Field(..., ge=0, le=100, description="Deterministic risk index (0-100)")
    risk_level: str = Field(..., description="Risk category: CRITICAL, HIGH, MEDIUM, LOW")
    contributing_factors: List[str] = Field(default_factory=list, description="Explicit factor breakdown")
    calculation_version: str = "v1.0-deterministic"

    model_config = ConfigDict(extra="forbid")


class CalculateRiskScoreTool(BaseAgentTool):
    """Deterministic tool for calculating explainable operational risk."""

    @property
    def name(self) -> str:
        return "calculate_risk_score"

    @property
    def description(self) -> str:
        return (
            "Calculates a reproducible, explainable 0-100 operational risk score based on "
            "physical detection telemetry, defect spread, component criticality, recurrence, and service age."
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return RiskScoreInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return RiskScoreOutput

    def execute(self, params: RiskScoreInput) -> RiskScoreOutput:
        """Executes deterministic risk calculation formula."""
        factors: List[str] = []
        score = 10  # Baseline operational floor

        # 1. Defect Quantity & Confidence
        if params.defect_count > 0:
            defect_pts = min(params.defect_count * 5, 20)
            score += defect_pts
            factors.append(f"{params.defect_count} physical defect region(s) detected (+{defect_pts} pts).")

            if params.max_confidence >= 0.8:
                score += 10
                factors.append(f"High-confidence computer vision detection ({params.max_confidence*100:.1f}%, +10 pts).")
            elif params.max_confidence >= 0.5:
                score += 5
                factors.append(f"Moderate-confidence CV detection ({params.max_confidence*100:.1f}%, +5 pts).")

        # 2. Defect Geometry (Area & Length)
        if params.max_affected_area_percentage >= 4.0:
            score += 20
            factors.append(f"Extensive surface area coverage ({params.max_affected_area_percentage:.2f}%, +20 pts).")
        elif params.max_affected_area_percentage >= 2.0:
            score += 10
            factors.append(f"Moderate surface area coverage ({params.max_affected_area_percentage:.2f}%, +10 pts).")

        if params.max_crack_length_pixels >= 200.0:
            score += 15
            factors.append(f"Significant linear crack length ({params.max_crack_length_pixels:.1f}px, +15 pts).")
        elif params.max_crack_length_pixels >= 80.0:
            score += 8
            factors.append(f"Noticeable linear crack indication ({params.max_crack_length_pixels:.1f}px, +8 pts).")

        # 3. Recurrence & Maintenance History
        if params.recurrence_count >= 2:
            score += 20
            factors.append(f"Defect recurrence observed across {params.recurrence_count} previous inspection cycles (+20 pts).")
        elif params.recurrence_count == 1:
            score += 10
            factors.append("Defect recurrence observed in 1 prior inspection (+10 pts).")

        # 4. Component Criticality
        crit_upper = params.component_criticality.upper()
        if crit_upper == "CRITICAL":
            score += 15
            factors.append("Component classified as CRITICAL operational tier (+15 pts).")
        elif crit_upper == "HIGH":
            score += 10
            factors.append("Component classified as HIGH operational tier (+10 pts).")

        # 5. Service Age & Warranty
        if params.service_age_years is not None and params.service_age_years > 5.0:
            score += 10
            factors.append(f"Extended service operating age ({params.service_age_years} years, +10 pts).")

        if not params.has_active_warranty:
            score += 5
            factors.append("Asset operates outside original manufacturer warranty period (+5 pts).")

        # 6. Similar Historical Incidents
        if params.similar_incident_max_severity:
            inc_sev = params.similar_incident_max_severity.upper()
            if inc_sev in ("CRITICAL", "HIGH"):
                score += 15
                factors.append(f"Historical facility incident precedents confirm {inc_sev} failure mode risk (+15 pts).")

        # Clamp score [0, 100]
        final_score = min(max(score, 0), 100)

        # Risk Level
        if final_score >= 75:
            risk_level = "CRITICAL"
        elif final_score >= 50:
            risk_level = "HIGH"
        elif final_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        if not factors:
            factors.append("Asset operates within standard baseline tolerance with no defect indicators.")

        return RiskScoreOutput(
            risk_score=final_score,
            risk_level=risk_level,
            contributing_factors=factors,
            calculation_version="v1.0-deterministic"
        )


# Global tool instance
calculate_risk_score_tool = CalculateRiskScoreTool()
