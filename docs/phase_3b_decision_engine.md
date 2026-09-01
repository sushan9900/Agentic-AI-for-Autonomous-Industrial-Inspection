# Phase 3B: Agentic Inspection Decision Engine

## 1. Executive Summary & Architecture
Phase 3B implements the **Agentic Inspection Decision Engine**, an auditable multi-stage reasoning subsystem that consumes structured computer vision evidence (`VisionEvidence v1.0`), queries relational asset and failure histories, evaluates deterministic engineering rules, calculates explainable operational risk, and synthesizes draft maintenance work orders for human authorization.

```text
RAW INSPECTION IMAGE
        ↓
YOLO11n-seg Computer Vision Model
        ↓
VisionEvidence v1.0 (Geometric Detections & Cryptographic SHA-256)
        ↓
AGENTIC DECISION ENGINE (11 Explicit Observable Stages)
├── 1. Ingest Evidence
├── 2. Validate Evidence Schema
├── 3. Query Asset Context (Tool 1)
├── 4. Query Maintenance History (Tool 2)
├── 5. Query Engineering Thresholds (Tool 3)
├── 6. Check Similar Failure Incidents (Tool 4)
├── 7. Calculate Deterministic Risk Score (Tool 5)
├── 8. Formulate Authoritative Decision Policy
├── 9. Synthesize Work Order Recommendation (Local Gemma 3)
├── 10. Final Schema & Cross-Contract Validation
└── 11. Human Review Gate (Status: PENDING_HUMAN_REVIEW)
        ↓
PostgreSQL Persistence (agent_decisions & agent_reasoning_traces)
        ↓
Inspector Review Dashboard & Work-Order Approval
```

---

## 2. Tools Implemented
1. **`get_asset_context`**: Queries plant code, manufacturer, model, location, operating age, warranty status, and components.
2. **`get_maintenance_history`**: Retrieves past repair records, downtime, actual costs, and technician findings without fabrication.
3. **`get_severity_thresholds`**: Queries deterministic project-defined engineering threshold rules (`source_type="project_defined_rule"`).
4. **`check_similar_incidents`**: Queries past failure incidents and root causes from PostgreSQL.
5. **`calculate_risk_score`**: Computes an explainable 0–100 operational risk index.

---

## 3. Decision Policy Hierarchy
* **`URGENT_ENGINEERING_REVIEW`** (`CRITICAL` Priority): Risk score $\ge 75$, linear crack length $\ge 200\text{px}$, affected area $\ge 4.0\%$, or critical threshold violations.
* **`PRIORITY_MAINTENANCE`** (`HIGH` Priority): Risk score $\ge 50$, defect recurrence across inspections, or high-confidence indications.
* **`PLAN_MAINTENANCE`** (`MEDIUM` Priority): Risk score $\ge 25$ or established localized indications.
* **`SCHEDULE_INSPECTION`** (`LOW` Priority): Marginal confidence indications ($< 0.50$) or image blur warnings.
* **`MONITOR`** (`LOW` Priority): Baseline clean surface with zero defect indications.
* **`INSUFFICIENT_EVIDENCE`**: Triggered when perception evidence is invalid or incomplete.

---

## 4. REST API Endpoints
* `POST /api/v1/agent/inspect`: Triggers full 11-stage autonomous agent execution, persists decision and traces in PostgreSQL, returns `AgentInspectionDecision`.
* `GET /api/v1/agent/decisions/{decision_id}`: Retrieves stored decision record.
* `GET /api/v1/agent/decisions/{decision_id}/trace`: Retrieves sequential observable trace events.

---

## 5. Safety & Human-in-the-Loop Guardrails
* **Zero Autonomous Dispatch**: All work orders are initialized with `status = "PENDING_HUMAN_REVIEW"`.
* **Zero Paid APIs / Zero Cloud LLMs**: Exclusively local Ollama (`gemma3:latest`) and local PostgreSQL.
* **Deterministic Risk & Decisions**: The LLM does not arbitrarily assign numerical risk scores, costs, downtime, or override deterministic safety policies.
