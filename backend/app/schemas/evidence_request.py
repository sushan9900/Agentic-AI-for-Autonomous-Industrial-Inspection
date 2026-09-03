"""Pydantic v2 schemas for Evidence Request Planning (Phase 8E)."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceRequestType(str, Enum):
    """Categorization of targeted sensory evidence requests."""
    ADDITIONAL_IMAGE = "ADDITIONAL_IMAGE"
    HIGHER_RESOLUTION_IMAGE = "HIGHER_RESOLUTION_IMAGE"
    COMPONENT_CLOSEUP = "COMPONENT_CLOSEUP"
    ALTERNATE_VIEW = "ALTERNATE_VIEW"
    REPEAT_INSPECTION = "REPEAT_INSPECTION"
    METADATA_CONFIRMATION = "METADATA_CONFIRMATION"
    HISTORICAL_COMPARISON = "HISTORICAL_COMPARISON"


class EvidenceRequest(BaseModel):
    """
    Structured sensory or diagnostic evidence request.
    Generated when visual resolution or diagnostic coverage is insufficient.
    Strictly advisory: human_approval_required = True.
    """
    request_id: str = Field(..., description="Unique evidence request identifier")
    inspection_id: str = Field(..., description="Target inspection transaction ID")
    asset_id: str = Field(..., description="Target industrial asset ID")
    component_id: Optional[str] = Field(default=None, description="Target component ID")

    request_type: EvidenceRequestType = Field(..., description="Type of evidence requested")
    reason: str = Field(..., min_length=5, max_length=1000, description="Engineering rationale for evidence request")
    evidence_gap: str = Field(..., description="Specific diagnostic gap being addressed")

    required: bool = Field(default=True, description="Whether this evidence is required for definitive diagnostic closure")
    human_approval_required: bool = Field(default=True, description="Strict safety gate: human authorization required")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


class EvidenceRequestPlanResponse(BaseModel):
    """Envelope response for evidence requests generated for an inspection."""
    inspection_id: str
    total_requests: int
    requests: List[EvidenceRequest] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
