# Phase 7C: Prediction vs Outcome Analysis & Learning Metrics

## 1. Overview & Objective

Phase 7C implements deterministic statistical evaluation comparing model predictions against verified human review outcomes. It calculates agreement rates, confusion counts (false positives and false negatives), correction ratios, and severity estimation deltas.

## 2. Calculation Methodology

All metrics are calculated deterministically without the use of an LLM:

1. **Defect Agreement Rate:**
   $$\text{Defect Agreement} = \frac{\sum [ \text{ai\_defect\_detected} == \text{confirmed\_defect\_present} ]}{N}$$
2. **Severity Agreement Rate:**
   $$\text{Severity Agreement} = \frac{\sum [ \text{ai\_severity} == \text{confirmed\_severity} ]}{N}$$
3. **Risk-Band Agreement Rate:**
   $$\text{Risk-Band Agreement} = \frac{\sum [ \text{ai\_risk\_band} == \text{confirmed\_risk\_band} ]}{N}$$
   Risk bands: `CRITICAL` ($\ge 80$), `HIGH` ($\ge 60$), `MEDIUM` ($\ge 40$), `LOW` ($< 40$).
4. **False Positive Count & Rate:**
   Cases where AI detected a defect ($\text{ai\_defect\_detected} = \text{True}$), but human confirmed defect was absent ($\text{confirmed\_defect\_present} = \text{False}$).
5. **False Negative Count & Rate:**
   Cases where AI missed a defect ($\text{ai\_defect\_detected} = \text{False}$), but human confirmed defect was present ($\text{confirmed\_defect\_present} = \text{True}$).
6. **Correction Rate:**
   $$\text{Correction Rate} = \frac{\text{Count}(\text{review\_status} \in \{\text{CORRECTED}, \text{REJECTED}\})}{N}$$
7. **Severity Delta:**
   $$\Delta_{\text{sev}} = \text{Rank}(\text{ai\_severity}) - \text{Rank}(\text{confirmed\_severity})$$
   - $\Delta_{\text{sev}} > 0$: AI severity overestimation.
   - $\Delta_{\text{sev}} < 0$: AI severity underestimation.

## 3. Recurring Pattern Detection (Phase 7D)

Discrepancies are grouped by `(asset_id, component_id)`. When $\ge 2$ occurrences are identified:
- `REPEATED_FALSE_POSITIVES`
- `REPEATED_FALSE_NEGATIVES`
- `RECURRING_SEVERITY_OVERESTIMATION`
- `RECURRING_SEVERITY_UNDERESTIMATION`
- `REPEATED_ACTION_DISAGREEMENT`

## 4. API Endpoints

- `GET /api/v1/inspections/learning/metrics`: Scoped summary metrics.
- `GET /api/v1/inspections/learning/patterns`: Active recurring error patterns.
