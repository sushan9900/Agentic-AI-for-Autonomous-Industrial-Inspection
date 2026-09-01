"""Agent tool for retrieving deterministic engineering severity thresholds (Phase 3B)."""

from typing import List, Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from backend.app.tools.base import BaseAgentTool


class SeverityThresholdRule(BaseModel):
    """Deterministic engineering rule specification."""
    rule_id: str
    defect_type: str
    asset_type: str
    threshold_metric: str
    threshold_value: float
    unit: str
    severity_level: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    rationale: str
    source_type: str = "project_defined_rule"

    model_config = ConfigDict(extra="forbid")


# Canonical repository of deterministic project-defined engineering thresholds
PROJECT_ENGINEERING_RULES: List[SeverityThresholdRule] = [
    # Crack Thresholds (Pipelines)
    SeverityThresholdRule(
        rule_id="RULE-CRACK-PL-001",
        defect_type="crack",
        asset_type="PIPELINE",
        threshold_metric="crack_length_pixels",
        threshold_value=200.0,
        unit="pixels",
        severity_level="CRITICAL",
        rationale="Linear crack length >= 200px indicates high risk of through-wall propagation in pressurized pipe segments."
    ),
    SeverityThresholdRule(
        rule_id="RULE-CRACK-PL-002",
        defect_type="crack",
        asset_type="PIPELINE",
        threshold_metric="affected_area_percentage",
        threshold_value=3.0,
        unit="percentage",
        severity_level="CRITICAL",
        rationale="Crack surface area coverage >= 3.0% represents extensive structural micro-fracture grouping."
    ),
    SeverityThresholdRule(
        rule_id="RULE-CRACK-PL-003",
        defect_type="crack",
        asset_type="PIPELINE",
        threshold_metric="crack_length_pixels",
        threshold_value=80.0,
        unit="pixels",
        severity_level="MEDIUM",
        rationale="Linear crack indication >= 80px requires ultrasonic verification and scheduled non-destructive evaluation."
    ),
    # Crack Thresholds (Storage Tanks & Structures)
    SeverityThresholdRule(
        rule_id="RULE-CRACK-TK-001",
        defect_type="crack",
        asset_type="STORAGE_TANK",
        threshold_metric="crack_length_pixels",
        threshold_value=150.0,
        unit="pixels",
        severity_level="CRITICAL",
        rationale="Shell course crack >= 150px threatens hydrostatic containment boundary."
    ),
    SeverityThresholdRule(
        rule_id="RULE-CRACK-ST-001",
        defect_type="crack",
        asset_type="STRUCTURAL_FRAME",
        threshold_metric="affected_area_percentage",
        threshold_value=2.5,
        unit="percentage",
        severity_level="HIGH",
        rationale="Structural load-bearing member crack indication >= 2.5% requires structural engineer assessment."
    ),
    # Corrosion Thresholds
    SeverityThresholdRule(
        rule_id="RULE-CORR-PL-001",
        defect_type="corrosion",
        asset_type="PIPELINE",
        threshold_metric="affected_area_percentage",
        threshold_value=15.0,
        unit="percentage",
        severity_level="CRITICAL",
        rationale="Widespread surface corrosion >= 15.0% presents imminent wall loss and rupture hazard."
    ),
    SeverityThresholdRule(
        rule_id="RULE-CORR-PL-002",
        defect_type="corrosion",
        asset_type="PIPELINE",
        threshold_metric="affected_area_percentage",
        threshold_value=5.0,
        unit="percentage",
        severity_level="MEDIUM",
        rationale="Localized corrosion >= 5.0% requires protective coating reapplication and wall survey."
    ),
]


class SeverityThresholdInput(BaseModel):
    """Input parameters for get_severity_thresholds tool."""
    defect_type: Optional[str] = Field(default=None, description="Target defect category (e.g. 'crack', 'corrosion')")
    asset_type: Optional[str] = Field(default=None, description="Target asset category (e.g. 'PIPELINE', 'STORAGE_TANK')")

    model_config = ConfigDict(extra="forbid")


class SeverityThresholdOutput(BaseModel):
    """Structured output for get_severity_thresholds tool."""
    rules_count: int
    rules: List[SeverityThresholdRule] = Field(default_factory=list)
    source_type: str = "project_defined_rule"

    model_config = ConfigDict(extra="forbid")


class GetSeverityThresholdsTool(BaseAgentTool):
    """Tool for retrieving deterministic project engineering thresholds."""

    @property
    def name(self) -> str:
        return "get_severity_thresholds"

    @property
    def description(self) -> str:
        return (
            "Retrieves deterministic project-defined engineering threshold rules, metric limits, "
            "and severity classifications for given defect types and asset categories."
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return SeverityThresholdInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return SeverityThresholdOutput

    def execute(self, params: SeverityThresholdInput) -> SeverityThresholdOutput:
        """Filters engineering rules repository."""
        filtered = PROJECT_ENGINEERING_RULES

        if params.defect_type:
            d_type = params.defect_type.lower()
            filtered = [r for r in filtered if r.defect_type.lower() == d_type]

        if params.asset_type:
            a_type = params.asset_type.upper()
            filtered = [r for r in filtered if r.asset_type.upper() == a_type]

        return SeverityThresholdOutput(
            rules_count=len(filtered),
            rules=filtered,
            source_type="project_defined_rule"
        )


# Global tool instance
get_severity_thresholds_tool = GetSeverityThresholdsTool()
