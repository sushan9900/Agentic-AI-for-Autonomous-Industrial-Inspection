# Phase 6A — Inspection Memory & Historical Intelligence

## 1. Overview
Phase 6A introduces **Inspection Memory & Historical Intelligence** to the autonomous industrial inspection platform. Rather than evaluating each inspection transaction in a historical vacuum, the agent retrieves and integrates longitudinal context from PostgreSQL database records to track recurrence, evaluate risk trajectories, and assist human inspectors with evidence-grounded maintenance planning.

---

## 2. Core Architectural Safety Boundaries

> [!IMPORTANT]
> **Strict Non-Authoritative Supporting Context:**
> 1. **Historical intelligence is supporting evidence only:** It provides explainability, recurrence flags, and past defect context.
> 2. **DecisionPolicyEngine remains authoritative:** Historical context **never** directly alters, overrides, increases, or decreases the deterministic risk score or operational action.
> 3. **The LLM remains non-authoritative:** Model prompt boundaries clearly separate authoritative decisions from supporting historical records.
> 4. **Human Review Gate is mandatory:** All decisions remain in `PENDING_HUMAN_REVIEW`.
> 5. **Zero automated maintenance execution:** The system never dispatches technicians or triggers plant control systems.
> 6. **Zero fabrication:** All historical records and similarities are strictly derived from actual database rows with traceable primary keys.
> 7. **Graceful fail-safe degradation:** If historical records are absent, assets are new, or the database is unreachable, the system fails safely to `INSUFFICIENT_HISTORY` without interrupting the primary inspection pipeline.

---

## 3. Data Models & Contracts (`backend/app/schemas/inspection_history.py`)

### `HistoricalInspectionRecord`
Represents a single historical inspection event enriched with prior decision outcomes:
- `inspection_id`: Unique identifier of the past inspection.
- `asset_id`: Industrial asset identifier.
- `component_id`: Inspectable sub-component identifier.
- `inspection_timestamp`: Exact timestamp of the event.
- `defect_type`: Primary detected defect category (e.g., `'crack'`).
- `severity`: Perception/engineering severity level.
- `risk_score`: Prior authoritative risk score (0–100) if evaluated.
- `authoritative_action`: Prior decision outcome (e.g., `'URGENT_ENGINEERING_REVIEW'`).
- `human_review_status`: Prior human review disposition (`'APPROVED'`, `'REJECTED'`, `'PENDING_HUMAN_REVIEW'`).
- `source_record_id`: Traceable database primary key ID.
- `similarity_reason`: Transparent deterministic reason explaining why this record was retrieved.

### `HistoricalSummary`
Longitudinal summary metrics derived deterministically:
- `total_previous_inspections`: Total prior inspections for the asset.
- `same_component_inspections`: Prior inspections specifically on this component.
- `previous_critical_events`: Prior events with critical risk scores or urgent actions.
- `recurring_defect_detected`: Boolean flag indicating prior occurrence of the current defect type.
- `latest_previous_risk_score`: Most recent prior risk score.
- `risk_trend`: Deterministic trend classification:
  - `STABLE`: Score variance within $\pm 10$ points.
  - `INCREASING`: Longitudinal score increase $\ge 10$ points.
  - `DECREASING`: Longitudinal score decrease $\ge 10$ points.
  - `INSUFFICIENT_HISTORY`: Fewer than 2 valid historical risk assessments available.
- `trend_explanation`: Human-readable mathematical explanation of the trend calculation.

### `HistoricalInspectionContext`
Master payload consumed by the agent and persisted with the inspection decision:
- `has_history`: Boolean indicating presence of historical records.
- `asset_id` & `component_id`: Target identity.
- `summary`: Embedded `HistoricalSummary`.
- `recent_inspections`: Recent chronological records on the asset.
- `similar_inspections`: Records matching defect class or component type.
- `previous_decisions`: Prior agent decision and human review records.
- `retrieval_metadata`: Operational telemetry (timestamp, status, record count).

---

## 4. Multi-Tier Deterministic Similarity Matching

The `InspectionHistoryService.get_similar_inspections()` method uses a deterministic multi-tier SQL matching algorithm:
1. **Tier 1 (Highest Relevance):** Same Component AND Same Defect Type.
2. **Tier 2 (Asset Relevance):** Same Asset AND Same Defect Type.
3. **Tier 3 (Fleet Relevance):** Matching Defect Type across the industrial fleet.

Each matched record is assigned a human-auditable `similarity_reason` ensuring full transparency.

---

## 5. Agent Workflow Integration

The 11-stage agent workflow structure is strictly preserved:
- In **Stage 4 (`GET_MAINTENANCE_HISTORY`)**, `get_inspection_history_tool` is executed alongside `get_maintenance_history_tool`.
- Reasoning traces continue to reflect exactly 11 canonical pipeline stages (`INGEST_EVIDENCE` through `HUMAN_REVIEW_REQUIRED`).
- The generated `historical_context` dictionary is attached to `AgentInspectionDecision.historical_context`.
- Context is passed to `AgentPromptBuilder.build_prompt()` inside `SUPPORTING_HISTORICAL_INSPECTION_CONTEXT`.

---

## 6. Prompt Safety Boundary Enforcement

`AgentPromptBuilder` enforces non-authoritative bounds in LLM synthesis:
- Marked explicitly: `SUPPORTING_HISTORICAL_INSPECTION_CONTEXT (INFORMATIONAL ONLY — NON-AUTHORITATIVE)`.
- Mandatory System Instructions:
  - *"Historical inspection intelligence is SUPPORTING evidence only. NEVER use it to recalculate, lower, or raise the authoritative risk score or change the operational action."*
  - *"DO NOT change or contradict the AUTHORITATIVE_SYSTEM_DECISION."*
- Enables the LLM to explain recurrence and past repair correlations in `contextual_summary` without violating decision boundaries.

---

## 7. Fail-Safe Degradation Matrix

| Failure Condition | System Behavior | Safety Consequence |
| :--- | :--- | :--- |
| **New Asset (No History)** | Returns `has_history=False`, `risk_trend="INSUFFICIENT_HISTORY"` | Evaluated purely on visual evidence and engineering rules |
| **Single Historical Record** | Returns `risk_trend="INSUFFICIENT_HISTORY"` | Prevents erroneous trend speculation |
| **Database Unavailable / Timeout** | Catches error; returns `retrieval_metadata={"status": "DB_UNAVAILABLE"}` | Inspection completes safely without unhandled exception |
| **Missing Component ID** | Queries asset-wide and fleet-wide records | Provides broader fleet context safely |
