"""Strict Pydantic v2 schemas for the Agentic Decision Engine (Phase 2A)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InspectionPriority(str, Enum):
    """Operational priority for industrial maintenance attention."""
    LOW = "LOW"                          # Minor visual indication or clean surface
    MEDIUM = "MEDIUM"                    # Measurable indication requiring scheduled monitoring
    HIGH = "HIGH"                        # Significant structural defect requiring expedited maintenance
    CRITICAL = "CRITICAL"                # Major structural integrity threat requiring immediate action
    REVIEW_REQUIRED = "REVIEW_REQUIRED"  # Visual evidence degraded or uncertain; human expert review mandatory


class DecisionConfidence(str, Enum):
    """Confidence tier of the decision engine based on visual quality and model score."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceValueState(str, Enum):
    """Explicit state classification for evidence properties to prevent hallucinated defaults."""
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RuleEvaluation(BaseModel):
    """Individual rule execution result explaining a deterministic decision factor."""
    rule_id: str = Field(..., description="Canonical rule identifier (e.g. 'RULE-SEV-001')")
    rule_name: str = Field(..., description="Human-readable rule name")
    triggered: bool = Field(..., description="Whether rule conditions were satisfied")
    severity: InspectionPriority = Field(..., description="Priority severity level contributed by this rule")
    explanation: str = Field(..., description="Auditable justification based strictly on observed evidence")
    evidence_fields_used: List[str] = Field(
        default_factory=list,
        description="List of exact evidence attribute paths evaluated by this rule"
    )

    model_config = ConfigDict(extra="forbid")


class DecisionTraceStep(BaseModel):
    """Auditable chronological decision lifecycle trace step (NOT chain-of-thought)."""
    step_number: int = Field(..., ge=1, description="Sequential trace step index")
    action: str = Field(..., description="Action performed (e.g. 'VALIDATE_EVIDENCE', 'EVALUATE_RULE')")
    inputs_used: Dict[str, Any] = Field(default_factory=dict, description="Input parameters consumed in this step")
    output_summary: str = Field(..., description="Summary of step output")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of step execution"
    )

    model_config = ConfigDict(extra="forbid")


class EvidenceReference(BaseModel):
    """Cryptographic and contextual linkage back to source inspection evidence."""
    source_image_filename: str = Field(..., description="Source image filename")
    source_image_sha256: str = Field(..., description="SHA-256 hash of raw input image")
    model_checkpoint_sha256: str = Field(..., description="SHA-256 hash of active model weights")
    detection_ids: List[str] = Field(default_factory=list, description="Referenced detection identifiers")

    model_config = ConfigDict(extra="forbid")


class InspectionDecision(BaseModel):
    """Authoritative, typed, and auditable inspection decision contract."""
    decision_id: str = Field(..., description="Unique deterministic decision identifier")
    schema_version: str = Field(default="1.0", description="Decision contract specification version")
    inspection_id: str = Field(..., description="Correlation ID linking to the original inspection")
    priority: InspectionPriority = Field(..., description="Aggregated operational maintenance priority")
    confidence: DecisionConfidence = Field(..., description="Confidence level in the decision aggregation")
    defect_summary: str = Field(..., description="Structured summary of physical defect findings")
    evidence_summary: str = Field(..., description="High-level synthesis of measurable visual evidence")
    recommended_action: str = Field(..., description="Standardized operational recommendation")
    requires_human_review: bool = Field(..., description="True if human inspector review is required")
    rule_evaluations: List[RuleEvaluation] = Field(default_factory=list, description="Results of all evaluated rules")
    evidence_references: EvidenceReference = Field(..., description="Cryptographic provenance references")
    decision_trace: List[DecisionTraceStep] = Field(default_factory=list, description="Auditable step trace")
    limitations: List[str] = Field(default_factory=list, description="Explicit operational and domain limitations")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC creation timestamp"
    )

    model_config = ConfigDict(extra="forbid")
