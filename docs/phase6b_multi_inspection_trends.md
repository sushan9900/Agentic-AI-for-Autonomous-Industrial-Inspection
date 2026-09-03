# Phase 6B — Multi-Inspection Trend Analysis

## 1. Overview
Phase 6B extends the Inspection Memory framework (introduced in Phase 6A) to perform deterministic, auditable **Multi-Inspection Trend Analysis** across chronological inspection series.

Moving beyond isolated past lookups, this subsystem systematically tracks:
- **Defect burden and progression** (count, spread, growth)
- **Physical severity evolution** (categorical and ordinal ranks)
- **Authoritative risk score trajectories**
- **Defect recurrence patterns** (persistent vs intermittent)
- **Inspection frequency acceleration or deceleration**
- **Holistic deterioration status**
- **Evidence sufficiency and confidence tiers**

---

## 2. Non-Negotiable Safety Invariants

> [!IMPORTANT]
> **Strict Non-Authoritative Supporting Context:**
> 1. **Historical trend analysis is SUPPORTING evidence only:** It never modifies, overrides, increases, or decreases the current in-flight inspection's deterministic risk score, severity rating, or operational action.
> 2. **DecisionPolicyEngine remains authoritative:** The current visual evidence and physical detection metrics strictly dictate the authoritative decision.
> 3. **The LLM remains strictly non-authoritative:** Model prompts isolate trends under non-authoritative blocks. The LLM is forbidden from predicting exact future failure dates or overriding decisions.
> 4. **Human Review Gate remains mandatory:** All generated work orders remain in `PENDING_HUMAN_REVIEW`.
> 5. **Zero automated maintenance execution:** The system never dispatches technicians or triggers plant control systems.
> 6. **Zero fabrication:** All historical series points are strictly grounded in real database rows with traceable primary keys.
> 7. **Graceful fail-safe degradation:** Missing records, single inspections, or database timeouts degrade safely to `INSUFFICIENT_HISTORY` without crashing the primary inspection pipeline.

---

## 3. Trend Data Contracts (`backend/app/schemas/inspection_trend.py`)

### Time-Series Observation Models
- **`DefectObservationPoint`**: Tracks `timestamp`, `inspection_id`, `defect_type`, `defect_count`, `affected_area_percentage`, `crack_length_pixels`, and `source_record_id`.
- **`SeverityObservationPoint`**: Tracks `timestamp`, `inspection_id`, `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), ordinal `severity_rank` (1–4), and `source_record_id`.
- **`RiskScoreObservationPoint`**: Tracks `timestamp`, `inspection_id`, `risk_score` (0–100), `risk_level`, and `source_record_id`.
- **`InspectionIntervalPoint`**: Tracks `from_inspection_id`, `to_inspection_id`, and `interval_days`.

### Master Container: `InspectionTrendAnalysis`
- `asset_id`: Target industrial asset identifier.
- `component_id`: Target sub-component identifier.
- `inspection_count`: Total valid historical inspections analyzed.
- `analysis_window_days`: Total duration spanning earliest to latest inspection.
- `defect_series`, `severity_series`, `risk_series`, `interval_series`: Sorted chronological observation series.
- `average_interval_days`, `minimum_interval_days`, `maximum_interval_days`.
- `defect_trend`: `INCREASING`, `STABLE`, `DECREASING`, or `INSUFFICIENT_HISTORY`.
- `severity_trend`: `INCREASING`, `STABLE`, `DECREASING`, or `INSUFFICIENT_HISTORY`.
- `risk_trend`: `INCREASING`, `STABLE`, `DECREASING`, or `INSUFFICIENT_HISTORY`.
- `recurrence_pattern`: `NO_RECURRENCE`, `RECURRENT`, `PERSISTENT`, or `INSUFFICIENT_HISTORY`.
- `frequency_trend`: `FREQUENCY_INCREASING`, `FREQUENCY_STABLE`, `FREQUENCY_DECREASING`, or `INSUFFICIENT_HISTORY`.
- `deterioration_status`: `DETERIORATING`, `STABLE`, `IMPROVING`, `RECURRENT_RISK`, or `INSUFFICIENT_HISTORY`.
- `evidence_sufficiency`: `SUFFICIENT`, `LIMITED`, or `INSUFFICIENT`.
- `source_inspection_ids`: Comprehensive list of all inspection IDs contributing to the trend.
- `trend_summary_explanation`: Human-auditable synthesis of findings.

---

## 4. Deterministic Methodologies

### Defect Progression
Evaluates the chronological delta between earliest and latest observations:
- $\Delta \text{count} > 0$: **`INCREASING`** (Defect count/burden is worsening).
- $\Delta \text{count} < 0$: **`DECREASING`** (Defect count has reduced).
- $\Delta \text{count} == 0$: **`STABLE`** (Defect count is consistent).
- Fewer than 2 observations: **`INSUFFICIENT_HISTORY`**.

### Severity Progression (Ordinal Ranking)
Categorical severity is mapped onto an explicit ordinal ranking:
$$\text{LOW } (1) < \text{MEDIUM / MODERATE } (2) < \text{HIGH } (3) < \text{CRITICAL } (4)$$
- $\text{Rank}_{\text{latest}} > \text{Rank}_{\text{earliest}}$: **`INCREASING`** (Severity worsened).
- $\text{Rank}_{\text{latest}} < \text{Rank}_{\text{earliest}}$: **`DECREASING`** (Severity improved).
- $\text{Rank}_{\text{latest}} == \text{Rank}_{\text{earliest}}$: **`STABLE`** (Severity remained consistent).
- Fewer than 2 observations: **`INSUFFICIENT_HISTORY`**.

### Risk Score Trajectory
Evaluates the chronological trajectory of authoritative risk scores:
- $\Delta (\text{Score}_{\text{latest}} - \text{Score}_{\text{earliest}}) \ge +10$: **`INCREASING`**.
- $\Delta (\text{Score}_{\text{latest}} - \text{Score}_{\text{earliest}}) \le -10$: **`DECREASING`**.
- $|\Delta| < 10$: **`STABLE`**.
- Fewer than 2 assessments: **`INSUFFICIENT_HISTORY`**.

### Recurrence Analysis
Analyzes defect appearance patterns across chronological inspections:
- **`PERSISTENT`**: Defect detected across $\ge 2$ consecutive chronological inspections without intervening absence.
- **`RECURRENT`**: Defect detected across $\ge 2$ inspections with intermediate clean inspections (reappearance).
- **`NO_RECURRENCE`**: Defect detected only once or never in historical records.
- **`INSUFFICIENT_HISTORY`**: Fewer than 2 inspections or missing defect classification.

### Inspection Intervals & Frequency
Computes interval in days between consecutive inspections $t_i$ and $t_{i+1}$:
$$\text{interval\_days} = \frac{(t_{i+1} - t_i)_{\text{seconds}}}{86400.0}$$
Summary statistics: $\text{average\_interval}$, $\text{min\_interval}$, $\text{max\_interval}$.
Frequency velocity:
- $\text{interval}_{\text{recent}} \le 0.75 \times \text{interval}_{\text{prior\_avg}}$: **`FREQUENCY_INCREASING`** (Inspections accelerating).
- $\text{interval}_{\text{recent}} \ge 1.35 \times \text{interval}_{\text{prior\_avg}}$: **`FREQUENCY_DECREASING`** (Inspections slowing down).
- Otherwise: **`FREQUENCY_STABLE`**.

### Deterioration Status Synthesis
A transparent, deterministic synthesis combining independent trend signals:
1. **`DETERIORATING`**: Any of `defect_trend`, `severity_trend`, or `risk_trend` is `INCREASING` while none are `DECREASING`.
2. **`IMPROVING`**: Any of `defect_trend`, `severity_trend`, or `risk_trend` is `DECREASING` while none are `INCREASING`.
3. **`RECURRENT_RISK`**: `recurrence_pattern` is `PERSISTENT` or `RECURRENT` under elevated baseline risk ($\ge 60/100$).
4. **`STABLE`**: All available trends are `STABLE`.
5. **`INSUFFICIENT_HISTORY`**: Evidence sufficiency is `INSUFFICIENT`.

### Evidence Sufficiency
- **`SUFFICIENT`**: $\ge 3$ valid historical inspections with $\ge 2$ defect or risk observations.
- **`LIMITED`**: Exactly 2 valid historical inspections.
- **`INSUFFICIENT`**: $< 2$ valid historical inspections.

---

## 5. Agent Integration & Prompt Safety Boundary

- **Canonical 11-Stage Workflow:** Multi-inspection trend analysis is integrated inside **Stage 4 (`GET_MAINTENANCE_HISTORY`)**. The reasoning trace retains exactly 11 canonical stages.
- **Decision Contract:** The trend payload is attached to `AgentInspectionDecision.inspection_trends` and embedded in `execution_metrics`.
- **LLM Prompt Boundary:** Trends are presented within `SUPPORTING_HISTORICAL_INSPECTION_CONTEXT` with explicit negative constraints:
  - *"Historical inspection intelligence and multi-inspection trends are SUPPORTING evidence only. NEVER use it to recalculate, lower, or raise the authoritative risk score, change the operational action, remove human review, or invent future failure dates."*

---

## 6. Fail-Safe Degradation Matrix

| Failure Condition | Subsystem Response | Safety Consequence |
| :--- | :--- | :--- |
| **New Asset / Zero History** | Returns `inspection_count=0`, `deterioration_status="INSUFFICIENT_HISTORY"` | Evaluated purely on visual evidence and engineering rules |
| **Single Historical Record** | Returns `evidence_sufficiency="INSUFFICIENT"`, all trends `INSUFFICIENT_HISTORY` | Prevents erroneous trend speculation |
| **Missing Severity / Score Fields** | Skips missing fields while computing available metrics | Partial data used safely without crash |
| **Database Failure / Query Error** | Catches exception; returns safely degraded container with status `ERROR` | Primary inspection workflow continues uninterrupted |

---

## 7. Performance & Traceability
- **Zero N+1 Query Overhead:** Trends are calculated in-memory from the records retrieved in Phase 6A.
- **Zero Additional Infrastructure:** No external time-series or vector databases were introduced.
- **Full Traceability:** Every observation point maintains its exact `inspection_id` and database primary key.
