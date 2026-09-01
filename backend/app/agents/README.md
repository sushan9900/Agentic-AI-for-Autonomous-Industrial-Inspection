# Agentic Inspection Decision Engine (`backend/app/agents`)

The Agentic Decision Engine transforms structured Computer Vision perception contracts (`VisionEvidence v1.0`) into auditable, evidence-driven industrial decisions and draft maintenance work orders.

## Explicit 11-Stage Workflow
1. `INGEST_EVIDENCE`: Ingests and registers the incoming inspection transaction.
2. `VALIDATE_EVIDENCE`: Enforces schema conformance against `VisionEvidence v1.0` and verifies image hash.
3. `GET_ASSET_CONTEXT`: Queries physical asset specifications, age, operational status, and component hierarchy (`get_asset_context`).
4. `GET_MAINTENANCE_HISTORY`: Queries past repairs, downtime, actual costs, and technician notes (`get_maintenance_history`).
5. `GET_SEVERITY_THRESHOLDS`: Evaluates project-defined engineering threshold rules (`get_severity_thresholds`).
6. `CHECK_SIMILAR_INCIDENTS`: Retrieves historical facility failure incidents and corrective actions (`check_similar_incidents`).
7. `ASSESS_RISK`: Deterministically calculates a 0–100 operational risk index with explainable factor breakdown (`calculate_risk_score`).
8. `FORMULATE_DECISION`: Evaluates the deterministic hierarchy (`decision_policy_engine`) yielding an authoritative action:
   - `URGENT_ENGINEERING_REVIEW`
   - `PRIORITY_MAINTENANCE`
   - `PLAN_MAINTENANCE`
   - `SCHEDULE_INSPECTION`
   - `MONITOR`
   - `INSUFFICIENT_EVIDENCE`
9. `GENERATE_WORK_ORDER`: Uses local Ollama (Gemma 3) to draft contextual justifications, required NDE methods, and safety notes without hallucinating costs or downtime.
10. `FINAL_VALIDATION`: Cross-verifies evidence references and schema integrity.
11. `HUMAN_REVIEW_REQUIRED`: Enforces strict safety gate: assigns status `PENDING_HUMAN_REVIEW`. Zero automated dispatch.
