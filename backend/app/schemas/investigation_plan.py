"""Pydantic v2 schemas for Agentic Investigation Planning (Phase 6C)."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


InvestigationPriorityLiteral = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CauseConfidenceLiteral = Literal["LOW", "MEDIUM", "HIGH"]
InformationGapImportanceLiteral = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
EvidenceSufficiencyLiteral = Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT"]


class InvestigationCause(BaseModel):
    """Evidence-grounded suspected contributing factor or defect mechanism."""
    cause: str = Field(..., description="Suspected physical or operational defect mechanism")
    rationale: str = Field(..., description="Engineering rationale based on visual evidence and history")
    confidence: CauseConfidenceLiteral = Field(..., description="Confidence tier: LOW, MEDIUM, HIGH")
    supporting_evidence: List[str] = Field(default_factory=list, description="Grounding evidence facts")
    source_ids: List[str] = Field(default_factory=list, description="Traceable inspection or decision record IDs")

    model_config = ConfigDict(extra="forbid")


class DiagnosticStep(BaseModel):
    """Ordered, non-destructive diagnostic investigation instruction."""
    step_number: int = Field(..., ge=1, description="Sequential execution step number")
    action: str = Field(..., description="Specific diagnostic inspection action to perform")
    purpose: str = Field(..., description="Engineering objective of this diagnostic step")
    expected_observation: str = Field(..., description="Anticipated findings if suspected cause is correct")
    confirms_if: str = Field(..., description="Observation that strengthens the suspected cause")
    weakens_if: str = Field(..., description="Observation that weakens or disconfirms the suspected cause")
    evidence_required: List[str] = Field(default_factory=list, description="Specific telemetry or NDE required")
    human_required: bool = Field(default=True, description="Strict safety constraint: always requires human execution")

    model_config = ConfigDict(extra="forbid")


class EvidenceReference(BaseModel):
    """Traceable provenance link to authoritative inspection telemetry or historical records."""
    reference_type: str = Field(..., description="Category: VISUAL_DETECTION, HISTORICAL_RECORD, TREND_ANALYSIS, ENGINEERING_RULE")
    reference_id: str = Field(..., description="Identifier of the referenced artifact or record")
    description: str = Field(..., description="Summary of evidence contribution")

    model_config = ConfigDict(extra="forbid")


class InformationGap(BaseModel):
    """Explicitly identified unknown or unverified engineering factor."""
    field: str = Field(..., description="Unobserved engineering or operational parameter")
    reason: str = Field(..., description="Why this information is absent from visual perception")
    importance: InformationGapImportanceLiteral = Field(..., description="Severity impact of this missing parameter")
    verification_method: str = Field(..., description="How a human inspector can obtain or verify this data")

    model_config = ConfigDict(extra="forbid")


class HumanReviewPoint(BaseModel):
    """Mandatory human inspector authorization and sanity-check checkpoint."""
    checkpoint: str = Field(..., description="Specific safety or technical verification checkpoint")
    reason: str = Field(..., description="Safety justification for mandatory human verification")
    required: bool = Field(default=True, description="Strict safety gate: always True")

    model_config = ConfigDict(extra="forbid")


class InvestigationPlan(BaseModel):
    """
    Structured Decision-Support Investigation Plan.
    Provides diagnostic recommendations without executing maintenance or modifying controls.
    """
    plan_id: str = Field(..., description="Unique deterministic identifier for this investigation plan")
    inspection_id: str = Field(..., description="Associated inspection transaction ID")
    asset_id: str = Field(..., description="Associated industrial asset ID")
    component_id: Optional[str] = Field(default=None, description="Associated inspectable component ID")
    priority: InvestigationPriorityLiteral = Field(..., description="Investigation urgency priority tier")
    objective: str = Field(..., description="Primary engineering objective of this investigation")
    primary_question: str = Field(..., description="Core operational question to be answered by inspection")

    # Diagnostic & Causal Framework
    suspected_causes: List[InvestigationCause] = Field(default_factory=list, description="Evidence-grounded potential causes")
    diagnostic_steps: List[DiagnosticStep] = Field(default_factory=list, description="Sequential non-destructive diagnostic steps")

    # Traceability & Basis
    evidence_basis: List[EvidenceReference] = Field(default_factory=list, description="Grounding links to current visual evidence")
    historical_basis: List[str] = Field(default_factory=list, description="Grounding references to Phase 6A memory")
    trend_basis: List[str] = Field(default_factory=list, description="Grounding references to Phase 6B multi-inspection trends")

    # Epistemic Transparency
    information_gaps: List[InformationGap] = Field(default_factory=list, description="Explicitly identified unobserved parameters")
    confirmation_signals: List[str] = Field(default_factory=list, description="Observations that corroborate suspected causes")
    disconfirmation_signals: List[str] = Field(default_factory=list, description="Observations that refute suspected causes")

    # Safety Guardrails
    human_review_points: List[HumanReviewPoint] = Field(default_factory=list, description="Mandatory human inspector verification checkpoints")
    constraints: List[str] = Field(
        default_factory=lambda: [
            "Decision support only: zero automated maintenance execution.",
            "Zero plant-control modification or PLC/SCADA override.",
            "Mandatory human sign-off required prior to technician dispatch."
        ],
        description="Operating guardrails and negative boundaries"
    )
    safety_notes: List[str] = Field(default_factory=list, description="Site safety hazard mitigations")
    evidence_sufficiency: EvidenceSufficiencyLiteral = Field(default="INSUFFICIENT", description="Historical and visual data confidence")
    source_inspection_ids: List[str] = Field(default_factory=list, description="Traceable past inspection transactions")
    generated_by: str = Field(default="deterministic_investigation_planner_v1", description="Planner algorithm identifier")
    authoritative: bool = Field(default=False, description="Strict safety invariant: investigation plans are never authoritative")

    model_config = ConfigDict(extra="forbid")
