# Phase 2A: Agentic Decision Engine Foundation

## 1. Overview & Purpose
Phase 2A establishes the deterministic, versioned, and auditable decision layer of the **Agentic AI for Autonomous Industrial Inspection** platform.

It bridges the gap between the Computer Vision Perception layer (which outputs `VisionEvidence` v1.0 contracts) and the downstream Agentic AI Reasoning layer, without introducing provider lock-in, ungrounded LLM hallucinations, or unverified automated work-order dispatches.

```text
RAW INSPECTION IMAGE
        ↓
VISION MODEL (YOLO11n-seg)
        ↓
VISION EVIDENCE (v1.0)
        ↓
EVIDENCE ADAPTER
        ↓
DETERMINISTIC RULE ENGINE (7 Rules)
        ↓
DECISION AGGREGATION
        ↓
INSPECTION DECISION (Auditable Contract)
        ↓
FUTURE AGENTIC LAYER [Phase 2B/2C]
```

---

## 2. Core Architectural Principles
1. **Model & Provider Independence**: The decision engine is decoupled from specific model architectures and LLM providers.
2. **Zero Hallucination / No Fabricated Data**: Missing evidence fields are strictly tracked as `UNKNOWN` or `NOT_APPLICABLE` rather than substituted with guessed values.
3. **Auditable Decision Trace**: Every decision contains chronological lifecycle trace steps (`INGEST_EVIDENCE`, `NORMALIZE_EVIDENCE`, `EVALUATE_RULES`, `AGGREGATE_DECISION`) with explicit rule outcomes.
4. **Development/Research Threshold Calibration**: Rule thresholds in `configs/decision_rules.yaml` are explicitly documented as development-only and are not certified field limits.
5. **Mandatory Human-in-the-Loop Safeguards**: High-priority, critical, and quality-degraded decisions explicitly set `requires_human_review = True`.

---

## 3. Implemented Engineering Rules

| Rule ID | Rule Name | Description | Severity Contributed |
| :--- | :--- | :--- | :--- |
| **`RULE-QUAL-001`** | Image Quality Impairment Warning | Triggers if blur, low contrast, or exposure flags are present. | `REVIEW_REQUIRED` |
| **`RULE-DET-000`** | No Defect Indications Detected | Triggers when detection count is 0 on a clear image. | `LOW` |
| **`RULE-SEV-001`** | High Defect Surface Area Coverage | Triggers if defect polygon area exceeds development thresholds ($\ge 5\%$ High, $\ge 12\%$ Critical). | `HIGH` / `CRITICAL` |
| **`RULE-SEV-002`** | Large Defect Spatial Bounding Region | Triggers if bounding region span exceeds frame coverage thresholds ($\ge 15\%$ High, $\ge 35\%$ Critical). | `HIGH` / `CRITICAL` |
| **`RULE-SEV-003`** | Extensive Crack Propagation Length | Triggers if continuous crack length exceeds pixel thresholds ($\ge 450\,\text{px}$ High, $\ge 750\,\text{px}$ Critical). | `HIGH` / `CRITICAL` |
| **`RULE-SEV-004`** | Multiple Defect Regions Detected | Triggers if defect cluster count is high ($\ge 3$ Medium, $\ge 6$ High). | `MEDIUM` / `HIGH` |
| **`RULE-CONF-001`** | Marginal Model Confidence Verification | Triggers if any detection has confidence below review limit ($< 0.35$). | `REVIEW_REQUIRED` |

---

## 4. Priority Aggregation Precedence

When multiple rules trigger, the aggregated priority is determined via strict precedence:
$$\text{CRITICAL} \succ \text{HIGH} \succ \text{REVIEW\_REQUIRED} \succ \text{MEDIUM} \succ \text{LOW}$$

---

## 5. Future Phase 2 Roadmap & Integration Points

- **Phase 2B (Context & RAG Retrieval)**:
  - Integration of historical component inspection databases.
  - Incident retrieval / RAG over past failure reports and asset manuals.
  - Claude / LLM multi-modal reasoning over `AgentState`.
- **Phase 2C (Operational Action & Work Orders)**:
  - Automated draft work-order generation.
  - Human inspector sign-off workflow and threshold overrides.
