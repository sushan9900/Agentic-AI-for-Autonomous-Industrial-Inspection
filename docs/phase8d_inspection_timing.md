# Phase 8D: Inspection Timing Recommendations

## 1. Overview & Objective

Phase 8D provides transparent, deterministic timing window recommendations for industrial inspection tasks. It evaluates defect severity, structural risk scores, deterioration dynamics, and defect recurrence patterns to suggest appropriate scheduling urgency.

## 2. Deterministic Timing Windows

| Condition | Timing Window | Urgency |
| :--- | :--- | :--- |
| $\text{Risk} \ge 80 \text{ (CRITICAL)} \land \text{Deteriorating}$ | `IMMEDIATE` | CRITICAL |
| $\text{Risk} \ge 80 \text{ (CRITICAL)} \lor (\text{Risk} \ge 60 \land \text{Deteriorating})$ | `WITHIN_24_HOURS` | HIGH |
| $\text{Risk} \ge 60 \text{ (HIGH)} \lor \text{Recurrence} \in \{\text{PERSISTENT}, \text{RECURRENT}\}$ | `WITHIN_7_DAYS` | MEDIUM |
| $\text{Risk} \ge 40 \text{ (MEDIUM)}$ | `WITHIN_30_DAYS` | LOW |
| $\text{Risk} < 40 \text{ (Nominal / Low)}$ | `ROUTINE` | LOW |

## 3. Pure Deterministic Execution

- No LLM hallucination or generative variability is permitted in scheduling timing windows.
- Output includes explicit supporting factors explaining the deterministic rule firing.
- Timing recommendations are advisory only (`authoritative = False`).
