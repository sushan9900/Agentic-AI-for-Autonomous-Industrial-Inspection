# Phase 8A: Inspection Task Lifecycle

## 1. Overview & Objective

Phase 8A establishes the formal operational inspection task lifecycle and immutable transition ledger. While previous phases performed automated vision inference, deterministic risk calculation, and historical learning, Phase 8A provides the foundational task structures to track and coordinate real engineering inspections through auditable lifecycle states.

## 2. Lifecycle States & Actor Types

### Deterministic Lifecycle States
- `CREATED`: Newly instantiated task waiting for initial queue assignment.
- `QUEUED`: Placed in the engineering review / inspection queue.
- `ASSIGNED_FOR_REVIEW`: Assigned to a designated inspector or specialist.
- `IN_REVIEW`: Currently being actively examined by an inspector.
- `AWAITING_EVIDENCE`: Paused pending collection of additional imagery or NDE readings.
- `REVIEWED`: Completed diagnostic review; awaiting final disposition.
- `COMPLETED`: Finalized by an authorized human inspector.
- `CANCELLED`: Cancelled prior to completion.
- `REJECTED`: Rejected during inspection or approval review.

### Actor Classifications
- `SYSTEM_RECOMMENDATION`: Automated orchestration agent generating recommendations.
- `HUMAN_REVIEWER`: Authorized human inspector or plant engineer.
- `SYSTEM_VALIDATION`: Automated data validation gates.

> **CRITICAL INVARIANT:**
> An actor of type `SYSTEM_RECOMMENDATION` is strictly prohibited from transitioning a task directly to `COMPLETED`. Only an authorized human workflow may finalize a task.

## 3. Database Persistence Model

- **`InspectionTaskModel` (`inspection_tasks`)**:
  Stores the current operational state, target asset, component ID, priority, recommended timing window, and payload metadata.
- **`InspectionTaskTransitionModel` (`inspection_task_transitions`)**:
  Immutable audit ledger recording every state change with previous state, new state, actor type, actor ID, and justification reason.
