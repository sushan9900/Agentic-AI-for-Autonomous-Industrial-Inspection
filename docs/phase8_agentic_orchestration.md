# Phase 8: Agentic Inspection Orchestration & Closed-Loop Review

## 1. Executive Summary

Phase 8 elevates the industrial inspection intelligence platform into a fully coordinated, deterministic orchestration layer. By integrating perception outputs, deterministic safety policies, multi-inspection memory, degradation trends, investigation planning, human review outcomes, and adaptive intelligence, Phase 8 establishes a complete operational inspection lifecycle.

```
+---------------------------------------------------------------------------------------+
|                                    PHASE 8 WORKFLOW                                   |
+---------------------------------------------------------------------------------------+
|  [Multi-Phase Intelligence]                                                           |
|       - Vision Evidence (v1.0 / v2.0)                                                 |
|       - Authoritative Risk & Action (DecisionPolicyEngine)                            |
|       - Historical Memory & Trend Intelligence (Phases 6A & 6B)                       |
|       - Human Outcomes & Adaptive Insights (Phase 7)                                  |
|                                     |                                                 |
|                                     v                                                 |
|  [Phase 8C & 8D: Task & Timing Recommendation Engine]                                 |
|       - Generates explainable, advisory recommendations                               |
|       - Deterministically evaluates timing windows (IMMEDIATE, 24H, 7D, 30D, ROUTINE) |
|       - Strictly advisory: authoritative = False, human_approval_required = True      |
|                                     |                                                 |
|                                     v                                                 |
|  [Phase 8F: Human Approval Gatekeeper]                                                |
|       - PENDING -> APPROVED / MODIFIED / REJECTED                                     |
|       - No automated execution or dispatch without human authorization                |
|                                     | (Authorized Approval)                           |
|                                     v                                                 |
|  [Phase 8A & 8B: Deterministic Inspection Task Lifecycle]                             |
|       - CREATED -> QUEUED -> IN_REVIEW <-> AWAITING_EVIDENCE                          |
|                                   |                                                   |
|                                   v                                                   |
|                              [REVIEWED]                                               |
|                                   | (HUMAN_REVIEWER ONLY)                             |
|                                   v                                                   |
|                              [COMPLETED]                                              |
|                                     |                                                 |
|                                     v                                                 |
|  [Phase 8E: Evidence Request Planner]                                                 |
|       - Targets specific physical gaps (macro closeup, alternate angles, resolution)  |
+---------------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Components

### A. Lifecycle Finite State Machine (Phases 8A & 8B)
- **Task States:** `CREATED`, `QUEUED`, `ASSIGNED_FOR_REVIEW`, `IN_REVIEW`, `AWAITING_EVIDENCE`, `REVIEWED`, `COMPLETED`, `CANCELLED`, `REJECTED`.
- **Actor Classifications:** `SYSTEM_RECOMMENDATION`, `HUMAN_REVIEWER`, `SYSTEM_VALIDATION`.
- **Strict Invariants:**
  - `SYSTEM_RECOMMENDATION` can NEVER finalize tasks into `COMPLETED`.
  - Only an authorized `HUMAN_REVIEWER` can finalize tasks into `COMPLETED`.
  - Terminal states (`COMPLETED`, `CANCELLED`, `REJECTED`) permit zero outgoing transitions.
  - Every transition produces an immutable audit record in `inspection_task_transitions`.

### B. Task Recommendation Engine (Phase 8C)
- **Categories:**
  - `CREATE_INSPECTION`: Asset or component elapsed nominal inspection interval.
  - `REVIEW_EXISTING_INSPECTION`: Critical or high-priority inspection pending human review.
  - `REQUEST_ADDITIONAL_EVIDENCE`: Visual evidence insufficient or specific physical gaps unobserved.
  - `REPEAT_INSPECTION`: Active physical deterioration detected across historical scans.
  - `REQUIRE_EXPERT_REVIEW`: Complex defect or historical action disagreements.
- **Strict Safety:** All recommendations carry `authoritative = False` and `human_approval_required = True`.

### C. Deterministic Timing Window Evaluator (Phase 8D)
- Multi-factor deterministic rule matrix mapping risk scores, physical severity, deterioration dynamics, and recurrence patterns into exact scheduling windows (`IMMEDIATE`, `WITHIN_24_HOURS`, `WITHIN_7_DAYS`, `WITHIN_30_DAYS`, `ROUTINE`).
- Zero generative LLM variability.

### D. Evidence Request Planner (Phase 8E)
- Analyzes diagnostic gaps (e.g., defect depth, wall loss, coverage occlusion, low-confidence detections).
- Formulates structured requests: `COMPONENT_CLOSEUP`, `HIGHER_RESOLUTION_IMAGE`, `ALTERNATE_VIEW`, `ADDITIONAL_IMAGE`, `HISTORICAL_COMPARISON`.
- Never claims unobserved evidence already exists.

### E. Human Approval Gatekeeper (Phase 8F)
- Recommends operational actions to plant engineers.
- Engineering review statuses:
  - `APPROVED`: Instantiates operational task with original parameters.
  - `MODIFIED`: Adjusts urgency, timing, or task type; preserves modifications diff and original recommendation.
  - `REJECTED`: Declines recommendation; records reason; spawns zero tasks.
- Single disposition invariant: cannot re-process an already finalized approval.

---

## 3. Database Schema

1. **`inspection_tasks`**:
   - `id`, `task_id` (unique, indexed), `inspection_id`, `asset_id`, `component_id`, `state`, `task_type`, `priority`, `timing_window`, `assigned_to`, `payload`, `created_at`, `updated_at`.
2. **`inspection_task_transitions`**:
   - `id`, `transition_id` (unique, indexed), `task_id`, `inspection_id`, `previous_state`, `new_state`, `actor_type`, `actor_id`, `reason`, `transition_metadata`, `created_at`.
3. **`orchestration_approvals`**:
   - `id`, `approval_id` (unique, indexed), `recommendation_id`, `task_id`, `status`, `reviewer_id`, `reviewer_comment`, `original_recommendation`, `modifications`, `reviewed_at`, `created_at`.

---

## 4. REST API Reference

| Method | Endpoint | Summary |
| :--- | :--- | :--- |
| `POST` | `/api/v1/inspections/tasks` | Create inspection task |
| `GET` | `/api/v1/inspections/tasks` | List paginated inspection tasks with filters |
| `GET` | `/api/v1/inspections/tasks/{task_id}` | Get task detail and transition history |
| `POST` | `/api/v1/inspections/tasks/{task_id}/transition` | Execute authorized state transition |
| `GET` | `/api/v1/inspections/orchestration/recommendations` | Get active advisory task recommendations |
| `POST` | `/api/v1/inspections/orchestration/{recommendation_id}/approve` | Human approval of recommendation |
| `POST` | `/api/v1/inspections/orchestration/{recommendation_id}/reject` | Human decline of recommendation |
| `GET` | `/api/v1/inspections/orchestration/approvals` | List historical approval gate records |
| `GET` | `/api/v1/inspections/orchestration/audit` | Query immutable state transition audit ledger |
| `GET` | `/api/v1/inspections/{inspection_id}/evidence-requests` | Plan targeted evidence requests |

---

## 5. Inspection Operations Dashboard UI

Integrated into the operator workstation:
- **Operations Tab:** Accessible via navigation bar.
- **KPI Metrics:** Pending Approvals, Active Tasks, In Review, Completed Tasks.
- **Advisory Notice:** Prominently highlights advisory-only nature and human authorization prerequisite.
- **Recommendations Queue:** Displays active recommendations with direct `[Approve & Schedule]` and `[Decline]` actions.
- **Operational Tasks Table:** Real-time visibility into active task states with action buttons to advance lifecycle.
- **Audit Ledger:** Chronological, tamper-evident record of all state transitions.
