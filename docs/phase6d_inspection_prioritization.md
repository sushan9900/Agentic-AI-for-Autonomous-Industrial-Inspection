# Phase 6D — Agentic Inspection Prioritization & Scheduling

**Project:** Agentic AI for Autonomous Industrial Inspection
**Module:** `backend/app/services/inspection_prioritization.py`
**Endpoint:** `GET /api/v1/agent/inspections/prioritized`
**Status:** Completed & Validated

> [!IMPORTANT]
> **Safety Notice:**
> Phase 6D prioritizes human inspection review. It does not autonomously schedule maintenance or dispatch technicians. The derived `priority_score` and `priority_class` govern human inspector queue order only. They never modify or replace authoritative risk scores, physical severities, or operational actions established by the `DecisionPolicyEngine`. All inspections remain in `PENDING_HUMAN_REVIEW` until an authorized human inspector explicitly signs off.

---

## 1. Objective
Phase 6D introduces **Agentic Inspection Prioritization & Scheduling**. When hundreds of autonomous inspections are processed across industrial assets, inspectors need an explainable, deterministic ranking to determine which pending inspections warrant immediate human investigation.

The system synthesizes:
1. Authoritative risk scores and severities (`DecisionPolicyEngine`, Phase 3B/4),
2. Historical inspection intelligence (`HistoricalInspectionContext`, Phase 6A),
3. Multi-inspection trend analytics (`InspectionTrendAnalysis`, Phase 6B), and
4. Diagnostic investigation plans (`InvestigationPlan`, Phase 6C),

into a transparent, prioritized human review queue.

---

## 2. Safety Boundaries & Invariants

| Safety Invariant | Architectural Enforcement |
| :--- | :--- |
| **INVARIANT-01: Risk Score Invariance** | `priority_score` never alters or recalculates `authoritative_risk_score`. |
| **INVARIANT-02: Action Invariance** | Priority ordering never alters `operational_action`. |
| **INVARIANT-03: Mandatory Review Gate** | `human_review_required` remains `True`; no automatic approval or bypass. |
| **INVARIANT-04: Pending Filter** | Approved (`APPROVED`) and rejected (`REJECTED`) inspections are excluded from the pending review queue. |
| **INVARIANT-05: Deterministic Ordering** | Priority scores and ranks are computed deterministically without randomness. |
| **INVARIANT-06: Deterministic Tie-Breaking** | Multi-key ordering resolves score ties identically every run. |
| **INVARIANT-07: LLM Exclusion** | The LLM never calculates priority scores or queue rankings. |
| **INVARIANT-08: Prompt-Injection Resistance** | Malicious text in evidence/rationale cannot alter priority score or review gates. |
| **INVARIANT-09: Zero Field Dispatch** | Zero technician routing or work order execution. |
| **INVARIANT-10: Zero Plant Control** | Zero PLC/SCADA commands, overrides, or setpoint changes. |

---

## 3. Authoritative vs. Derived Review Fields

The system enforces an explicit boundary between authoritative decisions and derived review prioritization:

```
AUTHORITATIVE DECISION (Immutable)         DERIVED REVIEW PRIORITY (Decision-Support)
----------------------------------         ------------------------------------------
• risk_score (0–100)                       • priority_score (0–100)
• risk_level (CRITICAL, HIGH, ...)         • priority_class (CRITICAL, HIGH, ...)
• operational_action                       • priority_rank (#1, #2, ...)
• human_review_required (True)             • rationale (Explainable factor synthesis)
• review_status (PENDING_HUMAN_REVIEW)     • authoritative = False
```

---

## 4. Deterministic Priority Scoring Formula

The derived review priority score is computed out of **100 maximum points**:

$$\text{Priority Score} = S_{\text{risk}} + S_{\text{sev}} + S_{\text{det}} + S_{\text{rec}} + S_{\text{ev}} + S_{\text{inv}} + S_{\text{age}}$$

### Point Breakdown:
1. **Risk Component (max 40 pts):**
   - $\text{risk} \ge 80$: **+40 pts**
   - $\text{risk} \ge 60$: **+30 pts**
   - $\text{risk} \ge 40$: **+20 pts**
   - $\text{risk} < 40$: **+10 pts**
2. **Physical Severity Component (max 20 pts):**
   - `CRITICAL`: **+20 pts**
   - `HIGH`: **+15 pts**
   - `MEDIUM` / `MODERATE`: **+10 pts**
   - `LOW`: **+5 pts**
   - `UNKNOWN`: **+0 pts**
3. **Deterioration Component (max 15 pts):**
   - `DETERIORATING`: **+15 pts**
   - `STABLE`: **+5 pts**
   - `IMPROVING` / `INSUFFICIENT`: **+0 pts**
4. **Recurrence Component (max 10 pts):**
   - `PERSISTENT`: **+10 pts**
   - `RECURRENT`: **+8 pts**
   - `NO_RECURRENCE`: **+2 pts**
   - `INSUFFICIENT` / `UNKNOWN`: **+0 pts**
5. **Evidence Sufficiency (max 5 pts):**
   - `SUFFICIENT`: **+5 pts**
   - `LIMITED`: **+3 pts**
   - `INSUFFICIENT` / `UNKNOWN`: **+1 / 0 pts**
6. **Investigation Priority (max 5 pts):**
   - `CRITICAL`: **+5 pts**
   - `HIGH`: **+4 pts**
   - `MEDIUM`: **+3 pts**
   - `LOW`: **+1 pt**
7. **Pending Review Age (max 5 pts):**
   - $\ge 72\text{h}$: **+5 pts**
   - $\ge 48\text{h}$: **+4 pts**
   - $\ge 24\text{h}$: **+3 pts**
   - $\ge 12\text{h}$: **+2 pts**
   - $\ge 1\text{h}$: **+1 pt**
   - $< 1\text{h}$ or unavailable: **+0 pts**

---

## 5. Priority Classes & Tie-Breaking

### Priority Class Mapping:
- **`CRITICAL`**: $\text{Score} \ge 80$
- **`HIGH`**: $60 \le \text{Score} < 80$
- **`MEDIUM`**: $40 \le \text{Score} < 60$
- **`LOW`**: $\text{Score} < 40$

### Multi-Key Deterministic Tie-Breaking:
When two inspections share the exact same `priority_score`, ranking is resolved deterministically by:
1. Higher authoritative `risk_score` (descending),
2. Higher physical severity rank (descending),
3. Deterioration status (`DETERIORATING` > `STABLE` > `IMPROVING`),
4. Recurrence pattern (`PERSISTENT` > `RECURRENT` > `NO_RECURRENCE`),
5. Older pending review age (descending),
6. `inspection_id` lexicographically ascending (unique, guaranteed tie-break).

---

## 6. API Endpoint

`GET /api/v1/agent/inspections/prioritized`

### Query Parameters:
- `status`: Filter by review status (default: `PENDING_HUMAN_REVIEW`).
- `priority_class`: Filter by class (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- `asset_id`: Restrict to specific asset.
- `component_id`: Restrict to specific component.
- `limit`: Maximum items to return (1–100, default: 50).

### Sample Response:
```json
{
  "generated_at": "2026-09-03T13:43:24.000Z",
  "total_pending": 63,
  "methodology_version": "1.0",
  "safety_notice": "This queue recommends human review order only. It does not authorize or execute maintenance.",
  "items": [
    {
      "inspection_id": "insp-11112-phase6c-validation",
      "decision_id": "dec-insp-11112-phase6c-validation-ASSET-PL-01",
      "asset_id": "ASSET-PL-01",
      "priority_rank": 1,
      "priority_class": "CRITICAL",
      "priority_score": 95,
      "authoritative_risk_score": 100,
      "severity": "CRITICAL",
      "operational_action": "URGENT_ENGINEERING_REVIEW",
      "review_status": "PENDING_HUMAN_REVIEW",
      "human_review_required": true,
      "deterioration_status": "DETERIORATING",
      "recurrence_pattern": "PERSISTENT",
      "investigation_plan_id": "plan-insp-11112-phase6c-validation-ASSET-PL-01",
      "rationale": "CRITICAL review priority (score 95/100) because authoritative risk is 100/100, physical severity is CRITICAL, trend is DETERIORATING, defect is PERSISTENT.",
      "contributing_factors": [
        "Authoritative Risk >= 80 (+40 pts)",
        "Physical Severity CRITICAL (+20 pts)",
        "Multi-Inspection Trend DETERIORATING (+15 pts)",
        "Historical Defect PERSISTENT (+10 pts)",
        "Evidence Sufficiency SUFFICIENT (+5 pts)",
        "Investigation Priority CRITICAL (+5 pts)",
        "Pending Review Age 0.6h (+0 pts)"
      ],
      "authoritative": false
    }
  ]
}
```

---

## 7. Dashboard Integration

In the Inspector Review Workstation (`frontend/`):
- Added **Review Priority** navigation tab (`tab-priority`).
- Prioritized Review Queue table displays:
  - `Rank` (#1, #2, ...)
  - `Asset ID`
  - `Component ID`
  - `Review Priority` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW` badges)
  - `Priority Score` (e.g. 95 / 100)
  - `Authoritative Risk` (e.g. 100 CRITICAL)
  - `Trend` (`DETERIORATING`, `STABLE`, etc.)
  - `Recurrence` (`PERSISTENT`, `RECURRENT`, etc.)
  - `Status` (`PENDING_HUMAN_REVIEW`)
  - Direct deep link: `Review →` button taking inspectors to the detailed inspection workstation view.

---

## 8. Verification Results

### Dedicated Test Suite (`backend/tests/test_inspection_prioritization.py`)
**26 passed, 0 failed in 2.31s (100% success)**:
- Score contributions for risk, severity, deterioration, recurrence, evidence, investigation, and review age.
- Classification bands and monotonic ordering.
- Deterministic tie-breaking across identical scores.
- Status filtering and completed review exclusion.
- Graceful degradation on missing historical, trend, or investigation plan metadata.
- Resistance against prompt injection attempts.
- Invariance of authoritative risk scores, actions, and review requirements.

### Real-Data Validation (`scripts/run_phase_6d_real_validation.py`)
Executed against real PostgreSQL database with persisted records:
- **Total Pending Reviews Evaluated:** 63 records.
- **Top-Ranked Inspection:** `insp-11112-phase6c-validation` (Real DeepCrack 11112 image) ranked **#1** with `priority_score: 95/100`, `priority_class: CRITICAL`, `authoritative_risk_score: 100/100`.
- **Query Performance:** 221.16 ms batch retrieval (zero N+1 queries).
- **Monotonicity Check:** 100% monotonic rank ordering across all queue items.

---

## 9. Known Limitations & Future Extensions
- **Batch Evaluation:** Prioritization is computed on-demand over PostgreSQL candidate records; for enterprise deployments exceeding 10,000 concurrent pending reviews, an asynchronous materialized ranking view could be introduced.
- **Reviewer Skill-Based Routing:** Future extensions can incorporate inspector specialization matching (e.g. routing weld indications to NDE Level III weld specialists).
