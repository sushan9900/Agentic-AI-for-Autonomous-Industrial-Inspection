# Agentic AI for Autonomous Industrial Inspection

An industry-oriented industrial inspection platform combining computer vision defect detection with an agentic AI decision-making layer for automated assessment, contextual reasoning, and maintenance recommendation workflows.

---

## 1. Project Purpose

The primary objective of this project is to bridge automated visual inspection with autonomous engineering reasoning. While computer vision reliably detects and segments physical anomalies (e.g., pipeline corrosion, cracks, coating damage), domain-specific decisions require context—such as historical inspection records, maintenance rules, operating parameters, and risk assessment protocols.

This platform automates the end-to-end inspection lifecycle while maintaining a human-in-the-loop governance structure:
1. Detect physical defects via specialized computer vision.
2. Structure detected anomalies into normalized inspection payloads.
3. Investigate context and severity using an Agentic AI workflow.
4. Synthesize risk assessments, maintenance actions, and work orders.
5. Provide domain engineers with clear review, override, and approval workflows.

---

## 2. Current Development Phase: PHASE 0 (FOUNDATION)

> [!IMPORTANT]
> **This project is currently in Phase 0 (Project Foundation).**
> - The current codebase establishes the baseline project layout, configuration, logging, and minimal FastAPI application.
> - Computer vision models, LLM agents, RAG vector stores, PostgreSQL persistence, frontend UI, and work order generation are **planned for subsequent phases and are not yet implemented**.

---

## 3. Planned Architecture & Pipeline

### End-to-End Inspection Pipeline
```text
Inspection Image / Video Feed
            ↓
  Computer Vision Detection
            ↓
Structured Defect Information (JSON)
            ↓
   Agentic AI Investigation
   ├── Maintenance History Retrieval
   ├── Industrial Severity Rules Engine
   └── Historical Incident Matching
            ↓
     Risk Assessment
            ↓
Maintenance Recommendation & Work Order Draft
            ↓
   Human Inspector Review (Approve / Modify / Reject)
```

### Key Architectural Principles
- **Decoupled Vision & Agent Layers**: The vision system operates as an independent perception module. It can be upgraded, replaced, or swapped (e.g., YOLO, Mask R-CNN, custom ViT) without altering agentic reasoning logic.
- **Provider-Agnostic LLM Layer**: The decision-making agent layer is designed to support multiple LLM backends through unified abstractions.
- **API-First Architecture**: Clean separation between API endpoints, business logic, schemas, and persistence layers.
- **Type Safety & Contracts**: Strict Pydantic models for all API request/response payloads and agent tool parameters.

---

## 4. Technology Stack

| Layer | Technology |
|---|---|
| **Backend API** | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| **Computer Vision (Planned)** | PyTorch, YOLOv8/YOLO11, OpenCV |
| **Agent & Reasoning (Planned)** | Claude API / Anthropic, LangGraph / State Machine |
| **Data & Retrieval (Planned)** | PostgreSQL, Vector Embeddings / RAG |
| **Frontend (Planned)** | React, TypeScript, TailwindCSS |
| **Testing & Quality** | Pytest, HTTPX |

---

## 5. Directory Structure

```text
agentic-industrial-inspection/
│
├── backend/
│   ├── app/
│   │   ├── api/          # API route definitions and versioning
│   │   │   └── v1/       # Version 1 API endpoints
│   │   ├── core/         # Settings, configuration, and logging
│   │   ├── models/       # Database / ORM models (future phases)
│   │   ├── schemas/      # Pydantic data schemas & contracts
│   │   ├── services/     # Business logic layer
│   │   ├── tools/        # Agent tools & functions (future phases)
│   │   ├── agents/       # Agentic state machines / graphs (future phases)
│   │   └── main.py       # FastAPI application entry point
│   │
│   └── tests/            # Backend unit and integration tests
│
├── vision/
│   ├── models/           # CV model definitions & weights
│   ├── datasets/         # Dataset handling & loaders
│   ├── preprocessing/    # Image/video pipelines & transformations
│   ├── inference/        # Model inference engine & postprocessing
│   ├── evaluation/       # Benchmark and validation scripts
│   └── tests/            # Vision unit tests
│
├── frontend/             # React/TypeScript web application (future phase)
│
├── data/
│   ├── raw/              # Raw inspection media and annotations
│   ├── processed/        # Processed and normalized datasets
│   └── sample/           # Sample test images for local verification
│
├── configs/              # Environment and model configurations
├── scripts/              # Automation and operational utility scripts
├── docs/                 # Architectural and API documentation
├── experiments/          # Research notebooks and training logs
├── logs/                 # Application and execution logs
│
├── .env.example          # Template environment variable configuration
├── .gitignore            # Version control exclusion rules
├── README.md             # Project documentation
└── requirements.txt      # Foundation Python dependencies
```

---

## 6. Setup & Installation

### Step 1: Create a Python Virtual Environment
Ensure you have Python 3.10 or higher installed.

```powershell
# Using Python 3.11/3.10 on Windows
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### Step 2: Configure Environment Variables
Copy `.env.example` to create your local `.env` file:

```powershell
cp .env.example .env
```

### Step 3: Install Foundation Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 7. Running the FastAPI Server

Start the development server using Uvicorn:

```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)

---

## 8. Verifying the Health Endpoint

### Using cURL:
```powershell
curl http://127.0.0.1:8000/api/v1/health
```

### Expected Response:
```json
{
  "status": "healthy",
  "service": "agentic-industrial-inspection"
}
```

---

## 9. Running Tests

Execute the automated test suite with `pytest`:

```powershell
pytest backend/tests -v
```