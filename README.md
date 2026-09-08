# Agentic AI for Autonomous Industrial Inspection

An industry-oriented intelligent inspection platform combining **computer vision**, **deterministic engineering decision logic**, **agentic investigation**, **inspection memory**, **adaptive learning**, and **human-governed operational orchestration**.

> **AI can investigate and recommend, but safety-critical operational decisions remain governed by deterministic policies and authorized human approval.**

---

## 1. Project Overview

Traditional visual inspection systems can identify physical anomalies such as cracks, corrosion, coating damage, or other surface defects. Detection alone, however, does not answer the engineering questions that follow:

- How severe is the defect?
- What is the associated operational risk?
- Has the same asset experienced similar issues before?
- Is the condition deteriorating?
- What evidence is still missing?
- When should the asset be inspected again?
- Should an inspection task be created?
- Does a recommendation require human approval?

This project addresses that complete workflow by connecting visual inspection evidence with structured engineering reasoning and operational review.

### Core lifecycle

```text
Inspection Evidence
        |
        v
Computer Vision / Defect Evidence
        |
        v
Normalized Inspection Record
        |
        v
Agentic Investigation
 +-----------+-----------+
 |           |           |
 v           v           v
Asset     History     Similar
Context   Retrieval   Incidents
        |
        v
Deterministic Risk & Decision Policy
        |
        v
Inspection / Maintenance Recommendation
        |
        v
Human Approval Gate
        |
        v
Inspection Task Lifecycle
        |
        v
Outcome & Historical Memory
        |
        v
Adaptive Learning / Future Recommendations
```

---

## 2. Current Project Status

The repository has progressed substantially beyond the original foundation phase.

| Phase | Capability | Status |
|---|---|---|
| Phase 1-4 | Foundation, inspection intelligence, decision and review workflows | Implemented |
| Phase 5 | Evaluation, benchmarking and reliability framework | Implemented |
| Phase 6A | Inspection memory | Implemented |
| Phase 6B | Multi-inspection trends | Implemented |
| Phase 6C | Agentic investigation planning | Implemented |
| Phase 6D | Inspection prioritization | Implemented |
| Phase 7 | Adaptive inspection learning | Implemented |
| Phase 8 | Agentic inspection orchestration and closed-loop review | Implemented |
| Phase 9 | Analysis / next-stage development | In progress |

The repository contains the backend services, agent layer, tools, database models, APIs, evaluation tests, reports, documentation, and vision experiment structure required for these capabilities.

---

## 3. Key Design Principles

### Human-in-the-loop safety

The platform does not allow the AI agent to independently finalize safety-critical operational tasks.

```text
authoritative = False
human_approval_required = True
```

Only an authorized human reviewer can finalize an inspection task into a completed operational state.

### Deterministic authority boundaries

LLM/agent reasoning can assist investigation and explanation, while authoritative risk and action decisions are governed by deterministic policy logic.

### Decoupled computer vision and reasoning

The perception layer is separated from the agentic decision layer so vision models can evolve independently from reasoning and orchestration.

### Structured contracts

The backend uses typed schemas and structured service interfaces for API payloads, agent state, tools, database models, and recommendations.

### Auditable operations

State changes and human decisions are represented through structured records and audit information.

---

## 4. System Architecture

```text
+---------------------------------------------------------------------+
|                    AUTONOMOUS INSPECTION PLATFORM                  |
+---------------------------------------------------------------------+
|                                                                     |
|  Vision / Inspection Evidence                                      |
|              |                                                      |
|              v                                                      |
|  +-------------------------+                                        |
|  | Inspection Intelligence |                                        |
|  +------------+------------+                                        |
|               |                                                     |
|               v                                                     |
|  +-------------------------------------------------------------+    |
|  |                    Agentic Investigation                    |    |
|  |                                                             |    |
|  | Asset Context | Inspection History | Similar Incidents     |    |
|  | Maintenance   | Risk Scoring      | Severity Thresholds    |    |
|  +---------------------------+---------------------------------+    |
|                              |                                      |
|                              v                                      |
|  +-------------------------------------------------------------+    |
|  |              Deterministic Decision Policy                 |    |
|  |                  Severity -> Risk -> Action                 |    |
|  +---------------------------+---------------------------------+    |
|                              |                                      |
|                              v                                      |
|  +-------------------------------------------------------------+    |
|  |             Recommendation & Orchestration                  |    |
|  | Task Recommendation | Timing | Evidence | Prioritization   |    |
|  +---------------------------+---------------------------------+    |
|                              |                                      |
|                              v                                      |
|  +-------------------------------------------------------------+    |
|  |                     Human Approval Gate                    |    |
|  |                   APPROVE / MODIFY / REJECT                |    |
|  +---------------------------+---------------------------------+    |
|                              |                                      |
|                              v                                      |
|  +-------------------------------------------------------------+    |
|  |               Inspection Task State Machine                |    |
|  | CREATED -> QUEUED -> REVIEW -> EVIDENCE -> REVIEWED -> DONE|    |
|  +---------------------------+---------------------------------+    |
|                              |                                      |
|                              v                                      |
|               Inspection Outcomes & Memory                         |
|                              |                                      |
|                              v                                      |
|                       Adaptive Learning                             |
|                                                                     |
+---------------------------------------------------------------------+
```

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| API Contracts | Pydantic |
| Database | PostgreSQL |
| ORM / Persistence | SQLAlchemy |
| Database Migrations | Alembic |
| Agent Layer | Python agent/state architecture |
| LLM Integration | Provider abstraction with Ollama support |
| Local LLM | Ollama |
| Testing | Pytest, HTTPX |
| Computer Vision | Python vision pipeline / DeepCrack experiments |
| Frontend | Web application structure under `frontend/` |
| Configuration | Environment-based configuration |
| Version Control | Git / GitHub |

---

## 6. Agentic Intelligence Layer

The agent architecture is organized under:

```text
backend/app/agents/
```

Important components include:

```text
contracts.py
decision_engine.py
decision_policy.py
inspection_agent.py
prompts.py
reasoning.py
state.py
trace.py
validators.py
work_order.py
```

The architecture separates agent state, reasoning, decision policy, validation, traceability, work-order logic, and structured contracts.

---

## 7. Agent Tools

The tool layer is located under:

```text
backend/app/tools/
```

Current tools include:

```text
asset_context.py
component_context.py
get_inspection_history.py
maintenance_history.py
risk_scoring.py
severity_thresholds.py
similar_incidents.py
```

These tools allow the agentic workflow to retrieve structured engineering context instead of relying solely on free-form model reasoning.

---

## 8. Inspection Intelligence Services

The service layer contains the main operational intelligence modules:

```text
backend/app/services/
```

Key services include:

```text
adaptive_recommendation.py
end_to_end_inspection.py
evidence_request_planner.py
inspection_history.py
inspection_learning.py
inspection_orchestrator.py
inspection_outcome.py
inspection_prioritization.py
inspection_task.py
inspection_task_recommender.py
inspection_timing.py
inspection_trend.py
investigation_planner.py
orchestration_approval.py
```

Together these provide inspection history, historical trends, deterioration analysis, investigation planning, prioritization, outcome tracking, adaptive recommendations, evidence requests, timing recommendations, task orchestration, and human approval.

---

## 9. Phase 6 - Inspection Memory & Intelligence

### Phase 6A - Inspection Memory

The system retains and retrieves previous inspection information so new inspections can be interpreted in historical context.

### Phase 6B - Multi-Inspection Trends

Multiple inspections can be compared to identify recurring defects, deterioration, changing severity, inspection frequency, and historical recurrence.

### Phase 6C - Agentic Investigation Planning

The system determines what contextual information should be investigated before forming a recommendation.

### Phase 6D - Inspection Prioritization

Inspection candidates can be prioritized using structured risk and historical information.

---

## 10. Phase 7 - Adaptive Inspection Learning

Phase 7 extends the platform from static recommendations toward outcome-aware learning.

Relevant services include:

```text
inspection_learning.py
inspection_outcome.py
adaptive_recommendation.py
```

Inspection outcomes and historical decisions can inform future recommendation logic while remaining constrained by the platform's safety and decision-policy boundaries.

---

## 11. Phase 8 - Closed-Loop Inspection Orchestration

Phase 8 establishes the operational inspection lifecycle.

### Task states

```text
CREATED
   |
QUEUED
   |
ASSIGNED_FOR_REVIEW
   |
IN_REVIEW
   |
AWAITING_EVIDENCE
   |
REVIEWED
   |
COMPLETED
```

Additional terminal states:

```text
CANCELLED
REJECTED
```

### Safety invariant

```text
SYSTEM_RECOMMENDATION
        |
        X
        |
   COMPLETED

HUMAN_REVIEWER
        |
        v
   COMPLETED
```

A system recommendation cannot independently finalize an operational task.

---

## 12. Phase 8 Recommendation Types

The orchestration layer supports:

- `CREATE_INSPECTION`
- `REVIEW_EXISTING_INSPECTION`
- `REQUEST_ADDITIONAL_EVIDENCE`
- `REPEAT_INSPECTION`
- `REQUIRE_EXPERT_REVIEW`

Recommendations are explicitly advisory and require human authorization.

---

## 13. Timing Recommendations

The timing engine uses deterministic evaluation rather than generative model output.

Supported timing windows:

```text
IMMEDIATE
WITHIN_24_HOURS
WITHIN_7_DAYS
WITHIN_30_DAYS
ROUTINE
```

Timing decisions can incorporate risk, physical severity, deterioration dynamics, and recurrence patterns.

---

## 14. Evidence Request Planning

The evidence request planner identifies missing or insufficient physical evidence.

Supported request types:

```text
COMPONENT_CLOSEUP
HIGHER_RESOLUTION_IMAGE
ALTERNATE_VIEW
ADDITIONAL_IMAGE
HISTORICAL_COMPARISON
```

The system is designed not to claim that unobserved evidence already exists.

---

## 15. Human Approval Workflow

```text
PENDING
   +-- APPROVED
   +-- MODIFIED
   +-- REJECTED
```

- **APPROVED:** Instantiates the operational task using the approved recommendation.
- **MODIFIED:** Allows reviewer changes while preserving the original recommendation and modification information.
- **REJECTED:** Declines the recommendation and creates no operational task.

A finalized approval cannot be processed again.

---

## 16. Database

Database models are located under:

```text
backend/app/database/models/
```

Current models include:

```text
agent_decision.py
asset.py
component.py
defect.py
incident.py
inspection.py
inspection_outcome.py
inspection_task.py
maintenance.py
review.py
work_order.py
```

Orchestration-related persistence includes:

```text
inspection_tasks
inspection_task_transitions
orchestration_approvals
```

Database schema changes are managed through:

```text
alembic/
```

---

## 17. REST API

API endpoints are organized under:

```text
backend/app/api/v1/
```

Endpoint modules include:

```text
agent.py
analytics.py
assessment.py
assets.py
components.py
decision.py
health.py
images.py
inspection_outcomes.py
llm.py
orchestration.py
reviews.py
system.py
```

### Phase 8 orchestration APIs

```text
POST /api/v1/inspections/tasks
GET  /api/v1/inspections/tasks
GET  /api/v1/inspections/tasks/{task_id}
POST /api/v1/inspections/tasks/{task_id}/transition

GET  /api/v1/inspections/orchestration/recommendations
POST /api/v1/inspections/orchestration/{recommendation_id}/approve
POST /api/v1/inspections/orchestration/{recommendation_id}/reject

GET /api/v1/inspections/orchestration/approvals
GET /api/v1/inspections/orchestration/audit

GET /api/v1/inspections/{inspection_id}/evidence-requests
```

---

## 18. Computer Vision

Computer vision is organized under:

```text
vision/
```

Inspection experiments are maintained under:

```text
experiments/vision/
```

The repository includes DeepCrack-related inspection experiments and evaluation artifacts.

The vision layer is intentionally decoupled from the agentic reasoning layer so different defect detection models can be evaluated independently.

---

## 19. Data Organization

```text
data/
├── raw/
├── processed/
└── sample/
```

The repository also contains:

```text
configs/
scripts/
docs/
experiments/
logs/
reports/
runs/
weights/
```

---

## 20. Documentation

Architecture and phase documentation is maintained in:

```text
docs/
```

Important documents include:

```text
phase_2a_decision_engine.md
phase_2b_historical_context.md
phase_2c_agentic_reasoning.md
phase_2d_human_review.md

phase_3a_asset_intelligence.md
phase_3b_decision_engine.md

phase6a_inspection_memory.md
phase6b_multi_inspection_trends.md
phase6c_agentic_investigation_planning.md
phase6d_inspection_prioritization.md

phase7_agentic_learning.md
phase7a_inspection_outcomes.md
phase7c_learning_metrics.md
phase7e_adaptive_recommendations.md

phase8_agentic_orchestration.md
phase8a_inspection_task.md
phase8b_orchestration.md
phase8c_task_recommendation.md
phase8d_inspection_timing.md
phase8e_evidence_requests.md
phase8f_human_approval.md
```

---

## 21. Reports & Evaluation

Evaluation artifacts are maintained under:

```text
reports/
├── phase5d/
├── phase7/
└── phase8/
```

The Phase 5D framework covers end-to-end performance and reliability evaluation.

---

## 22. Testing

The backend test suite covers APIs, services, database models, agent behavior, agent state, tools, reasoning traces, decision policies, safety invariants, LLM behavior, Ollama integration, inspection memory, trends, prioritization, learning, orchestration, human approval, evidence requests, timing, failure recovery, and Phase 5D evaluation.

Run the complete backend test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

### Latest verification

```text
327 passed
2 warnings
```

The warnings are non-blocking dependency/test warnings; the complete suite passed successfully.

---

## 23. Setup

### Requirements

- Python 3.10+
- PostgreSQL
- Git
- Node.js/npm for frontend work
- Ollama for the local LLM workflow

### Create virtual environment

```powershell
python -m venv .venv
```

### Activate on Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

Alternatively, run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe
```

### Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Configure the required local environment variables using the project's `.env.example`.

---

## 24. Database Migration Commands

Check current migration:

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

Check for schema differences:

```powershell
.\.venv\Scripts\python.exe -m alembic check
```

Create a migration after an intentional schema change:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"
```

Apply migrations:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

---

## 25. Run the Backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation:

```text
http://127.0.0.1:8000/api/v1/docs
```

ReDoc:

```text
http://127.0.0.1:8000/api/v1/redoc
```

Health endpoint:

```text
http://127.0.0.1:8000/api/v1/health
```

---

## 26. Project Structure

```text
Agentic-AI-for-Autonomous-Industrial-Inspection/
│
├── alembic/                  # Database migrations
├── backend/
│   ├── app/
│   │   ├── agents/           # Agentic reasoning and decision architecture
│   │   ├── api/              # FastAPI routes
│   │   ├── core/             # Configuration and infrastructure
│   │   ├── database/         # SQLAlchemy base and database models
│   │   ├── evaluation/       # Evaluation components
│   │   ├── llm/              # LLM provider integration
│   │   ├── models/           # Application models
│   │   ├── schemas/          # Pydantic contracts
│   │   ├── services/         # Inspection intelligence services
│   │   ├── tools/            # Agent tools
│   │   └── main.py            # FastAPI entry point
│   └── tests/                # Automated backend tests
├── configs/                  # Configuration
├── data/                     # Inspection data
├── docs/                     # Phase and architecture documentation
├── experiments/              # Research and model experiments
├── frontend/                 # Frontend application
├── logs/                     # Runtime logs
├── reports/                  # Evaluation and benchmark reports
├── runs/                     # Experiment artifacts
├── scripts/                  # Utility scripts
├── vision/                   # Computer vision pipeline
├── weights/                  # Model weights
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 27. Safety & Governance Model

The project is intentionally designed around constrained autonomy.

```text
                 +-----------------------+
                 |   AI / Agent Layer    |
                 | Investigation + Advice|
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Deterministic Policy  |
                 | Risk / Action Rules   |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Human Approval Gate   |
                 | Approve / Modify /    |
                 | Reject                |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 | Operational Task      |
                 | Lifecycle + Audit     |
                 +-----------------------+
```

The architecture emphasizes:

- explainability
- deterministic authority
- human authorization
- immutable transition history
- structured evidence
- controlled recommendations
- failure-mode testing

---

## 28. Development Roadmap

The next development stage should build on the completed Phase 8 closed-loop foundation.

Potential Phase 9 work includes:

- deeper system-level analysis
- cross-phase integration validation
- performance optimization
- operational dashboard refinement
- broader vision-to-agent integration
- additional reliability and failure-mode evaluation
- production-readiness assessment

Phase 9 implementation should preserve the safety and authority boundaries established in Phases 5-8.

---

## 29. Verification Checklist

Before committing major changes:

```powershell
git status
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Check database migration state:

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

Check schema consistency:

```powershell
.\.venv\Scripts\python.exe -m alembic check
```

Review changes:

```powershell
git diff
```

Then commit intentionally selected files:

```powershell
git add <files>
git commit -m "docs: update project documentation"
git push origin main
```

---

## 30. Project Philosophy

The goal is not simply to build an AI model that detects defects.

It is to build an **end-to-end industrial inspection intelligence system** in which perception, contextual reasoning, historical intelligence, deterministic engineering policy, adaptive learning, operational orchestration, and human governance work together.

The architecture moves from:

```text
Detect
  ↓
Understand
  ↓
Investigate
  ↓
Assess
  ↓
Recommend
  ↓
Review
  ↓
Execute
  ↓
Learn
```

while keeping safety-critical authority outside unrestricted generative reasoning.

---

**Project:** Agentic AI for Autonomous Industrial Inspection  
**Current milestone:** Phase 8 completed; Phase 9 analysis/development
