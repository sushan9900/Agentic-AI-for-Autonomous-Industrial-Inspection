# Phase 6C — Agentic Investigation Planning

**Project:** Agentic AI for Autonomous Industrial Inspection
**Module:** `backend/app/services/investigation_planner.py`
**Status:** Completed & Validated

> [!IMPORTANT]
> **Safety Notice:**
> The investigation planner is decision-support only. It does not authorize or execute maintenance, dispatch field technicians, or modify plant control systems (PLC/SCADA). All operational decisions remain strictly governed by the authoritative `DecisionPolicyEngine` and require human inspector sign-off (`PENDING_HUMAN_REVIEW`).

---

## 1. Objective
Phase 6C introduces **Agentic Investigation Planning** to the inspection platform. Beyond simple visual detection and historical lookup, the system automatically synthesizes:
1. Current high-resolution visual evidence (`VisionEvidence v1.0`),
2. Authoritative risk scores and operational actions (`DecisionPolicyEngine`),
3. Historical inspection intelligence (`HistoricalInspectionContext`, Phase 6A), and
4. Multi-inspection trend analytics (`InspectionTrendAnalysis`, Phase 6B),

to formulate a structured, prioritized, and auditable non-destructive diagnostic investigation plan.

---

## 2. Architecture & Pipeline Integration

The investigation planner functions as an evidence-grounded decision-support layer within the canonical **11-stage reasoning trace**:

```
Vision Evidence (YOLO11n-seg)
         ↓
Evidence Validation (AgentValidator)
         ↓
Asset Context & Maintenance History (Phase 6A)
         ↓
Multi-Inspection Trends (Phase 6B)
         ↓
Deterministic Risk Assessment (Stage 7: ASSESS_RISK)
         ↓
Authoritative Decision (Stage 8: FORMULATE_DECISION)
         ↓
Deterministic Investigation Planning (InvestigationPlanner)
         ↓
LLM Grounded Synthesis & Draft Work Order (Stage 9: GENERATE_WORK_ORDER)
         ↓
Human Review Gate (Stage 11: HUMAN_REVIEW_REQUIRED -> PENDING_HUMAN_REVIEW)
```

- **Zero N+1 Queries:** Reuses memory records and trend analysis already queried in Stage 4.
- **Trace Invariance:** Exactly 11 canonical trace events are recorded. Investigation planning is executed seamlessly between decision formulation and draft synthesis without adding trace steps.

---

## 3. Investigation Plan Schema Contract

The structured contract is defined in [`backend/app/schemas/investigation_plan.py`](file:///c:/sushan_repos/Agentic-AI-for-Autonomous-Industrial-Inspection/backend/app/schemas/investigation_plan.py):

```python
class InvestigationPlan(BaseModel):
    plan_id: str
    inspection_id: str
    asset_id: str
    component_id: Optional[str]
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    objective: str
    primary_question: str
    suspected_causes: List[InvestigationCause]
    diagnostic_steps: List[DiagnosticStep]
    evidence_basis: List[EvidenceReference]
    historical_basis: List[str]
    trend_basis: List[str]
    information_gaps: List[InformationGap]
    confirmation_signals: List[str]
    disconfirmation_signals: List[str]
    human_review_points: List[HumanReviewPoint]
    constraints: List[str]
    safety_notes: List[str]
    evidence_sufficiency: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT"]
    source_inspection_ids: List[str]
    generated_by: str = "deterministic_investigation_planner_v1"
    authoritative: bool = False
```

---

## 4. Deterministic Priority Rules

Investigation priority governs diagnostic urgency and inspector review queue routing. It does **not** override or replace the authoritative operational decision.

| Priority | Deterministic Criteria |
| :--- | :--- |
| **`CRITICAL`** | `risk_score >= 80` **OR** (`severity == "CRITICAL"` AND `deterioration_status == "DETERIORATING"`) **OR** (`recurrence_pattern in ("PERSISTENT", "RECURRENT")` AND `severity == "CRITICAL"`) |
| **`HIGH`** | `risk_score >= 60` **OR** `deterioration_status == "DETERIORATING"` **OR** (`recurrence_pattern in ("PERSISTENT", "RECURRENT")` AND `severity == "HIGH"`) |
| **`MEDIUM`** | `risk_score >= 40` **OR** `recurrence_pattern in ("PERSISTENT", "RECURRENT")` |
| **`LOW`** | All other conditions |

---

## 5. Evidence-Grounded Cause Reasoning

Suspected causes use calibrated non-speculative engineering language (*"Potential contributing factor"* rather than *"Confirmed root cause"*):
- **Progressive Defect Propagation:** Triggered if `deterioration_status == "DETERIORATING"` or `defect_count >= 2`.
- **Persistent Unresolved Indication:** Triggered if `recurrence_pattern == "PERSISTENT"` across consecutive inspections.
- **Intermittent Defect Re-emergence:** Triggered if `recurrence_pattern == "RECURRENT"` following prior clean inspections.
- **Localized Stress Concentration / Fatigue Initiation:** Triggered if severity is `CRITICAL` or `HIGH` with extensive crack length / area.
- **Baseline Establishment Required:** Triggered when no historical precedent exists (`evidence_sufficiency == "INSUFFICIENT"`).

---

## 6. Diagnostic Investigation Steps

Every plan generates ordered, non-destructive diagnostic actions that require human inspection (`human_required: True`):
1. **Visual & Optical Magnification Inspection:** Verify physical surface morphology against model bounding box coordinates.
2. **Historical Cross-Referencing / Baseline Logging:** Measure dimensional delta against prior records or register baseline geometry.
3. **Non-Destructive Examination (NDE):** Liquid Penetrant Testing (PT) or Ultrasonic Testing (UT) to determine subsurface crack depth and structural wall penetration.
4. **Operational Load & Environmental Review:** Correlate SCADA cyclic pressure, thermal transients, or vibration data with the defect location.
5. **Inspector Review Workstation Sign-Off:** Authoritative human engineer sign-off before technician dispatch or maintenance scheduling.

---

## 7. Confirmation & Disconfirmation Signals

To assist inspector decision-making, each plan enumerates empirical observations that strengthen or refute suspected hypotheses:

- **Confirmation Signals:**
  - Physical surface crack confirmed under optical magnification.
  - Subsurface structural wall thinning verified via ultrasonic NDE.
  - Defect dimensions exhibit measurable growth compared to baseline.
  - Acoustic emission sensors detect active crack propagation under cyclic operational load.
- **Disconfirmation Signals:**
  - Indication disappears upon surface cleaning or solvent wipe (superficial grease/dirt artifact).
  - Zero depth confirmed by depth gauge (protective coating scratch only).
  - Defect dimensions remain identical to initial manufacturing fabrication baseline.
  - Visual anomaly attributable to camera lens glare or uneven lighting.

---

## 8. Explicit Information Gaps

Rather than fabricating unknown facts, the planner explicitly exposes unobserved physical parameters:
- **Subsurface Defect Depth:** 2D surface imagery cannot measure volumetric wall penetration (`CRITICAL`, verified via Ultrasonic Testing).
- **Operational Load & Vibration History:** SCADA pressure and cyclic stress logs are absent from imagery (`HIGH`, verified via SCADA export).
- **Material Metallurgy & Fabrication Tolerances:** Material grade and allowable stress limits (`MEDIUM`, verified via engineering specification drawings).
- **Environmental Chemical Exposure:** Atmospheric salinity or chemical exposure (`LOW`, verified via atmospheric telemetry).

---

## 9. Integration with Phase 6A and Phase 6B
The planner seamlessly consumes:
- `HistoricalInspectionContext.summary` (total prior inspections, historical risk trend, recurrence flags).
- `InspectionTrendAnalysis` (defect progression, severity progression, risk trajectory, recurrence pattern, deterioration status, and evidence sufficiency).
All data is passed in-memory without duplicate SQL queries.

---

## 10. LLM Boundary & Prompt-Injection Resistance
- **Role Isolation:** The LLM serves solely to enrich textual explanations and refine questions for human inspectors.
- **Strict Invariants:** The prompt explicitly forbids the LLM from modifying the authoritative risk score, changing operational actions, bypassing human review, or issuing plant control commands.
- **Sanitization & Guardrails:** `AgentValidator.sanitize_investigation_plan_output()` scrubs prompt-injection vectors (e.g., *"ignore previous instructions"*, *"disable human review"*, *"modify PLC"*), enforcing `authoritative = False` and deterministic constraints.
- **Graceful Fallback:** If the LLM service is offline, times out, or outputs malformed JSON, the deterministic investigation plan operates unimpeded.

---

## 11. Validation Results

### Dedicated Suite (`backend/tests/test_investigation_planner.py`)
18 passed in 63.54s:
- Critical, High, Medium, and Low risk priority classification.
- Recurring, progressive, stable, and improving trend plans.
- Insufficient history and missing evidence handling.
- Unknown cause handling and explicit information gap tracking.
- Confirmation and disconfirmation signal generation.
- Mandatory human review enforcement.
- LLM non-authoritative boundary verification.
- Prompt injection resistance.
- Zero automated dispatch or plant control constraints.

### Real-Image Validation (`data/processed/deepcrack/yolo/images/test/11112.jpg`)
Executed via `scripts/run_phase_6c_real_validation.py` using trained checkpoint `best.pt`:
- **Model Inference:** 2 defects detected on real image.
- **Authoritative Risk Score:** 100/100 (`CRITICAL`).
- **Operational Decision:** `URGENT_ENGINEERING_REVIEW`.
- **Review Status:** `PENDING_HUMAN_REVIEW` (`human_review_required: True`).
- **Historical Intelligence:** 3 prior inspections retrieved, `DETERIORATING` trend, `PERSISTENT` recurrence.
- **Investigation Plan:** `plan-insp-11112-phase6c-validation-ASSET-PL-01` generated with `priority: CRITICAL`, `authoritative: False`, 5 diagnostic steps, 2 suspected causes, 4 information gaps, and 4 confirmation signals.
- **Safety Invariants:** 100% verified.

---

## 12. Known Limitations & Future Extensions
- **Depth Measurement:** Optical inspection cannot resolve subsurface depth; volumetric NDE data integration can be explored in future multi-modal sensor fusion phases.
- **SCADA Telemetry Integration:** Operational pressure and temperature logs are currently marked as information gaps to be verified by human inspectors; automated SCADA ingestion pipelines may be connected in later telemetry extensions.
