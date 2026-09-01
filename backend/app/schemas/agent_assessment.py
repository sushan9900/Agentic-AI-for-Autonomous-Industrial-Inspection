"""Strict Pydantic v2 schemas for Agent Inspection Assessment, Draft Work Order, and Reasoning Traces."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from vision.schemas.evidence import VisionEvidence


class AgentInspectionAssessment(BaseModel):
    """Authoritative agentic assessment synthesizing perception evidence, historical context, and engineering rules."""
    schema_version: str = Field(default="1.0", description="Contract version")
    assessment_id: str = Field(..., description="Unique assessment identifier")
    component_id: str = Field(..., description="Target industrial component identifier")
    inspection_reference: str = Field(..., description="Correlated inspection transaction ID")
    summary: str = Field(..., description="Executive summary of multi-modal findings")
    detected_defects: List[Dict[str, Any]] = Field(default_factory=list, description="Verified physical defect observations")
    historical_context_summary: str = Field(..., description="Synthesis of component maintenance and prior incident trends")
    reasoning: str = Field(..., description="Structured engineering reasoning articulating physical defect progression")
    risk_factors: List[str] = Field(default_factory=list, description="Identified operational, structural, or environmental risks")
    recommended_actions: List[str] = Field(default_factory=list, description="Prioritized recommendations for maintenance engineers")
    confidence: str = Field(..., description="Qualitative assessment confidence (LOW, MEDIUM, HIGH)")
    uncertainty: str = Field(..., description="Explicit statement of visual or historical uncertainty and limitations")
    human_review_required: bool = Field(default=True, description="Safety invariant: human inspector review is mandatory")
    source_references: Dict[str, Any] = Field(default_factory=dict, description="Cryptographic and relational provenance references")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_provenance: Dict[str, Any] = Field(default_factory=dict, description="LLM provider and model metadata")

    model_config = ConfigDict(extra="forbid")


class DraftWorkOrder(BaseModel):
    """Draft maintenance work order synthesized by the agentic assistant pending human review."""
    schema_version: str = Field(default="1.0", description="Contract version")
    draft_id: str = Field(..., description="Unique draft work order identifier")
    component_id: str = Field(..., description="Target industrial component identifier")
    inspection_reference: str = Field(..., description="Correlated inspection transaction ID")
    priority: str = Field(..., description="Operational priority (LOW, MEDIUM, HIGH, CRITICAL)")
    recommended_action: str = Field(..., description="Prescribed remediation or examination procedure")
    justification: str = Field(..., description="Detailed engineering rationale supporting the work order")
    required_inspection: str = Field(..., description="Specific verification method required (e.g. Ultrasonic NDT, Sa 2.5 Sandblasting)")
    suggested_team: str = Field(..., description="Suggested maintenance discipline or specialist team")
    estimated_downtime_hours: Optional[float] = Field(default=None, ge=0.0)
    estimated_cost: Optional[float] = Field(default=None, ge=0.0)
    supporting_evidence: List[str] = Field(default_factory=list, description="Specific visual detection IDs and measurements")
    historical_support: List[str] = Field(default_factory=list, description="Historical incident or maintenance precedents")
    uncertainty: str = Field(..., description="Operational uncertainty statement")
    approval_status: str = Field(default="PENDING_HUMAN_REVIEW", description="Approval lifecycle state (Never automatically approved)")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generated_by: str = Field(default="InspectionReasoningAgent", description="Generating agent identity")

    model_config = ConfigDict(extra="forbid")


class AgentReasoningTrace(BaseModel):
    """Auditable trace recording the full agentic multi-modal reasoning workflow."""
    trace_id: str = Field(..., description="Unique trace transaction identifier")
    component_id: str = Field(..., description="Target component identifier")
    input_evidence_references: Dict[str, Any] = Field(default_factory=dict)
    historical_context_references: Dict[str, Any] = Field(default_factory=dict)
    deterministic_decision_reference: Dict[str, Any] = Field(default_factory=dict)
    provider: str = Field(..., description="LLM provider name (e.g. 'ollama')")
    model: str = Field(..., description="Active LLM model name (e.g. 'gemma3:latest')")
    prompt_version: str = Field(default="1.0", description="Reasoning prompt template version")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    output_reference: str = Field(..., description="Assessment identifier")
    human_review_status: str = Field(default="PENDING_HUMAN_REVIEW")

    model_config = ConfigDict(extra="forbid")


class InspectionAssessmentRequest(BaseModel):
    """API request payload for executing agentic inspection assessment."""
    component_id: str = Field(..., description="Target component identifier in the asset database")
    vision_evidence: VisionEvidence = Field(..., description="Validated VisionEvidence v1.0 payload")

    model_config = ConfigDict(extra="forbid")


class InspectionAssessmentResponse(BaseModel):
    """API response payload containing synthesized assessment, draft work order, and trace."""
    assessment: AgentInspectionAssessment
    draft_work_order: DraftWorkOrder
    reasoning_trace: AgentReasoningTrace

    model_config = ConfigDict(extra="forbid")
