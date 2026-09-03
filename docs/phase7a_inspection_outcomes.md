# Phase 7A: Human Review Outcome Memory

## 1. Overview & Objective

The Human Review Outcome Memory service captures structured human engineering inspection review outcomes and snapshots corresponding AI model predictions at the exact time of review. This establishes a persistent, immutable ground-truth dataset that fuels downstream learning, agreement metrics, and recurring error pattern detection.

## 2. Architectural Boundaries & Safety Invariants

- **Decision Invariance:** The capture of a review outcome updates the review lifecycle state (`AgentDecisionModel.review_status`) to `APPROVED`, `CORRECTED`, or `REJECTED`, but **never** modifies the authoritative risk score (`risk_score`) or operational action (`operational_decision`).
- **Human Authority:** The human reviewer is the sole authority regarding ground truth. AI predictions are treated strictly as reference inputs.
- **Traceability:** Every recorded outcome generates a unique `outcome_id` (`out-{inspection_id}-{uuid}`), references the reviewer ID, and persists full JSON snapshots of both AI predictions and confirmed outcomes.
- **Zero Field Execution:** Recording an outcome does not trigger work order dispatch or field maintenance.

## 3. Data Contract

The structured contract is defined in `backend/app/schemas/inspection_outcome.py`:

```python
class ReviewOutcomeStatus(str, Enum):
    APPROVED = "APPROVED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"

class ReviewerCorrection(BaseModel):
    correction_type: CorrectionType
    corrected_severity: Optional[str]
    corrected_defect_type: Optional[str]
    corrected_action: Optional[str]
    justification: Optional[str]

class InspectionOutcomeCreate(BaseModel):
    reviewer_id: str
    review_status: ReviewOutcomeStatus
    confirmed_defect_present: bool
    confirmed_severity: str
    confirmed_defect_type: str
    reviewer_correction: Optional[ReviewerCorrection]
    reviewer_comment: Optional[str]
    confirmation_source: ConfirmationSource
    evidence_quality: EvidenceQuality
```

## 4. API Endpoints

- `POST /api/v1/inspections/{inspection_id}/outcome`: Records a structured review outcome. Returns HTTP 201 on success, HTTP 404 if inspection does not exist, and HTTP 409 if a duplicate outcome exists for the same inspection and reviewer.
- `GET /api/v1/inspections/outcomes`: Lists recorded outcomes with pagination (`limit`, `offset`) and optional filtering (`asset_id`, `component_id`, `review_status`).
- `GET /api/v1/inspections/outcomes/{inspection_id}`: Retrieves the recorded outcome for a specific inspection.
