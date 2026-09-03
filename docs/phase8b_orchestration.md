# Phase 8B: Orchestration State Machine

## 1. Overview & Objective

Phase 8B implements a deterministic finite state machine (FSM) controlling all operational transitions of inspection tasks. It enforces strict graph connectivity, validates actor authority, requires human authorization to finalize tasks, and maintains an immutable audit trail.

## 2. Transition Rules & Matrix

```
[CREATED] -------------> [QUEUED] -------------> [IN_REVIEW] <---------> [AWAITING_EVIDENCE]
    |                       |                         |
    |                       |                         v
    |                       |                    [REVIEWED]
    |                       |                         | (HUMAN_REVIEWER ONLY)
    v                       v                         v
[CANCELLED] / [REJECTED] <----------------------- [COMPLETED]
```

### Transition Validation Rules
1. **Connectivity:** Transitions must match the directed state graph. Any jump (e.g. `CREATED` to `COMPLETED`) is rejected with `InvalidStateTransitionError`.
2. **Safety Gate (HUMAN_REVIEWER Only):** `SYSTEM_RECOMMENDATION` is strictly prohibited from finalizing tasks to `COMPLETED`. Attempting this raises `UnauthorizedTransitionError`.
3. **Terminal Invariance:** Once a task reaches `COMPLETED`, `CANCELLED`, or `REJECTED`, no further outgoing transitions are permitted.
4. **Audit Logging:** Every transition atomically generates an immutable `InspectionTaskTransitionModel` entry with previous state, new state, actor type, actor ID, and justification reason.
