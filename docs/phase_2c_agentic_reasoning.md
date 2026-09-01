# Phase 2C: Agentic Reasoning & Draft Work-Order Synthesis

## 1. Overview & Architecture
Phase 2C introduces the **Local LLM Agentic Reasoning Layer** to the **Agentic AI for Autonomous Industrial Inspection** system.

Using a locally hosted, free model (**`gemma3:latest`** via **Ollama**), the system synthesizes:
1. **`VisionEvidence` v1.0** (Perception Layer detections, pixel/normalized bounding boxes, polygons, crack lengths, quality metrics)
2. **`HistoricalContext` v1.0** (PostgreSQL asset intelligence, component specifications, maintenance logs, prior inspections, work orders, incident trends)
3. **`InspectionDecision` v1.0** (Deterministic engineering rule evaluations and priority classifications)

to generate:
- **`AgentInspectionAssessment` v1.0** (Multi-modal engineering assessment with physical reasoning, risk factors, and uncertainties)
- **`DraftWorkOrder` v1.0** (Draft work order with mandatory human inspector review)
- **`AgentReasoningTrace` v1.0** (Full auditable lifecycle trace)

```text
               ┌───────────────────────┐
               │  RAW INSPECTION IMAGE │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   YOLO11n-seg MODEL   │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  VisionEvidence v1.0  │
               └─────┬───────────┬─────┘
                     │           │
     ┌───────────────┘           └──────────────┐
     ▼                                          ▼
┌─────────────────────────┐        ┌────────────────────────┐
│  POSTGRESQL ASSET DB    │        │ DETERMINISTIC DECISION │
│  (HistoricalContext)    │        │ (7 Engineering Rules)  │
└────────────┬────────────┘        └────────────┬───────────┘
             │                                  │
             └─────────────────┬────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │   INSPECTION PROMPT BUILDER   │
               │   (Structured Grounding)      │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │    LOCAL OLLAMA (Gemma 3)     │
               │    http://localhost:11434     │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │  REASONING & WORK ORDER SYNTH │
               ├───────────────────────────────┤
               │ • AgentInspectionAssessment   │
               │ • DraftWorkOrder (PENDING)    │
               │ • AgentReasoningTrace         │
               └───────────────────────────────┘
```

---

## 2. Strict Evidence Hierarchy
The reasoning engine enforces a strict grounding priority:
1. **Current Visual Perception (`VisionEvidence`)** — Ground truth visual observations; immutable.
2. **Deterministic Rules (`InspectionDecision`)** — Deterministic engineering thresholds; cannot be overridden by LLM.
3. **Verified Historical Context (`HistoricalContext`)** — Database asset logs, installation dates, materials.
4. **Historical Incident Reports** — Past mechanical/structural failure precedents.
5. **Model Inference / Hypotheses** — Engineering reasoning articulating failure modes and propagation risks.

---

## 3. Human-in-the-Loop & Safety Guardrails
- **Mandatory Review Flag**: `human_review_required = True` on all assessments.
- **Draft Status Invariant**: `DraftWorkOrder.approval_status = "PENDING_HUMAN_REVIEW"` (Never automatically `APPROVED`).
- **Zero CMMS Dispatch**: No automated external email, SMS, or dispatch actions.
- **Synthetic Data Labeling**: If input component context is tagged `source_type = "development_synthetic"`, the prompt explicitly warns `DATA PROVENANCE: DEVELOPMENT_SYNTHETIC`.
- **Zero Paid APIs**: Configured exclusively for local `ollama` HTTP endpoint.

---

## 4. API Endpoints

### A. LLM Health Check
`GET /api/v1/llm/health`
```json
{
  "provider": "ollama",
  "model": "gemma3:latest",
  "available": true,
  "details": "Ollama server online. Model 'gemma3:latest' is loaded and ready."
}
```

### B. Agentic Inspection Assessment
`POST /api/v1/inspection/assessment`
- Request: `{"component_id": "PIPE-SEG-4021", "vision_evidence": { ... }}`
- Response: `{"assessment": { ... }, "draft_work_order": { ... }, "reasoning_trace": { ... }}`

---

## 5. Error Handling & Resilience
- **404 Not Found**: If `component_id` is missing in PostgreSQL.
- **503 Service Unavailable**: If local Ollama server is offline.
- **504 Gateway Timeout**: If local LLM generation exceeds timeout threshold (`120s`).
- **422 Unprocessable Entity**: If LLM structured JSON output fails schema validation.
