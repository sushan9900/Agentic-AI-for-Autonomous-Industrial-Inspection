# Phase 7E: Adaptive Recommendations & Advisory Prioritization

## 1. Overview & Objective

Phase 7E synthesizes detected error patterns into explainable, non-authoritative engineering advisory recommendations. Phase 7F integrates these recommendations as an advisory overlay on top of the existing deterministic 100-point prioritization queue without mutating authoritative scores or ranks.

## 2. Recommendation Types

- `HIGHER_REVIEW_PRIORITY`: Generated when recurring false negatives or recurring severity underestimations are detected on a component. Advisory adjustment: $+10$ to $+15$ pts.
- `REQUEST_ADDITIONAL_EVIDENCE`: Generated when recurring false positives or severity overestimations indicate sensory noise or edge artifacts. Advisory adjustment: $-5$ to $0$ pts.
- `REPEAT_INSPECTION`: Generated when severe divergence or persistent defect state requires physical re-imaging.
- `REQUIRE_EXPERT_REVIEW`: Generated when repeated operational action modifications occur. Advisory adjustment: $+5$ pts.
- `WATCH_FOR_RECURRING_DEFECT`: Generated when multiple confirmed defect cycles are observed on the same component.

## 3. The Zero-Overwrite Invariant (INVARIANT-13)

Adaptive recommendations and their suggested score adjustments are strictly non-authoritative:
1. `authoritative = False` is explicitly declared on every recommendation and advisory payload.
2. The 100-point authoritative `priority_score` and `priority_class` assigned by `DecisionPolicyEngine` and `InspectionPrioritizationService` remain 100% untouched.
3. Queue sorting and tie-breaking operate exclusively on the authoritative score and primary keys.
4. The advisory score adjustment is displayed alongside the authoritative score as an advisory overlay.

## 4. API Endpoints

- `GET /api/v1/inspections/learning/recommendations`: Returns active adaptive recommendations.
- `GET /api/v1/agent/inspections/prioritized`: Includes optional `adaptive_advisory` overlay per item.
