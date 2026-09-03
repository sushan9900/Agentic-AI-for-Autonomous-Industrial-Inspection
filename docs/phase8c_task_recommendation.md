# Phase 8C: Inspection Task Recommendation Engine

## 1. Overview & Objective

Phase 8C implements an advisory intelligence engine that synthesizes multi-phase inspection intelligence (authoritative risk, physical severity, deterioration trajectory, defect recurrence patterns, evidence sufficiency, and historical learning) into actionable task recommendations.

## 2. Recommendation Types

- `CREATE_INSPECTION`: Recommended when an inspectable component has elapsed its nominal inspection cycle without recent verified data.
- `REVIEW_EXISTING_INSPECTION`: Recommended when a completed or pending inspection has high risk or priority and awaits human engineer validation.
- `REQUEST_ADDITIONAL_EVIDENCE`: Recommended when image quality is insufficient, coverage is partial, or specific diagnostic gaps (e.g. wall thickness, crack depth) are unobserved.
- `REPEAT_INSPECTION`: Recommended when active deterioration or severe defect recurrence requires expedited re-imaging.
- `REQUIRE_EXPERT_REVIEW`: Recommended when recurring action disagreements or high operational risk require senior specialist engineering signoff.

## 3. Safety Guarantees

- **Non-Authoritative:** Every recommendation carries `authoritative = False`.
- **Human Approval Mandatory:** Every recommendation requires explicit human engineering approval (`human_approval_required = True`) before any task can be queued or instantiated.
- **Zero Field Execution:** Recommendations cannot dispatch field personnel or execute maintenance.
