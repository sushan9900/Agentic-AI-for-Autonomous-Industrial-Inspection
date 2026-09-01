# Phase 2D: Human-in-the-Loop Inspection Review & Work-Order Approval

## 1. Overview & Architecture
Phase 2D implements an authorized inspector-facing **Human-in-the-Loop (HITL)** review workflow for the **Agentic AI for Autonomous Industrial Inspection** system.

The system ensures that **AI perception and LLM reasoning remain decision-support drafts**, guaranteeing that no maintenance action or work order is authorized without explicit human inspector verification and attribution.

```text
┌─────────────────────────┐
│   Agentic AI Pipeline   │
│  (Vision + Context+LLM) │
└────────────┬────────────┘
             │
             ▼ POST /api/v1/inspection/assessment
┌─────────────────────────┐
│  Assessment & Draft WO  │ (approval_status: PENDING_HUMAN_REVIEW)
└────────────┬────────────┘
             │
             ▼ POST /api/v1/reviews
┌─────────────────────────┐
│    INSPECTION REVIEW    │ ◄─── State: PENDING_HUMAN_REVIEW
│  (PostgreSQL Database)  │
└────────────┬────────────┘
             │
             ├─────────────────────────────────────────────────┐
             ▼                                                 ▼
┌─────────────────────────┐                       ┌─────────────────────────┐
│   INSPECTOR DASHBOARD   │                       │   IMMUTABLE AUDIT LOG   │
│   (Web User Interface)  │                       │   (ReviewAuditLog DB)   │
├─────────────────────────┤                       ├─────────────────────────┤
│ • Queue Filtering       │                       │ • REVIEW_CREATED        │
│ • Raw vs Overlay Image  │                       │ • REVIEW_OPENED         │
│ • Defect Breakdown      │                       │ • WORK_ORDER_EDITED     │
│ • LLM Reasoning Review  │                       │ • REVISION_REQUESTED    │
│ • Draft WO Field Editor │                       │ • WORK_ORDER_APPROVED   │
│ • Approve / Reject / Rev│                       │ • WORK_ORDER_REJECTED   │
└────────────┬────────────┘                       └─────────────────────────┘
             │
             ▼ Explicit Inspector Decision
   [ APPROVED / REJECTED ] (Zero Automatic External Dispatch)
```

---

## 2. Review State Machine & Transitions

The review lifecycle is strictly governed by a server-side state machine:

```text
              ┌──────────────────────────┐
              │  PENDING_HUMAN_REVIEW    │
              └───────┬─────────┬────────┘
                      │         │
           ┌──────────┘         └──────────┐
           ▼                               ▼
    ┌──────────────┐              ┌──────────────────┐
    │  IN_REVIEW   │              │REVISION_REQUESTED│
    └──────┬───────┘              └────────┬─────────┘
           │                               │
           ├───────────────────────────────┤
           ▼                               ▼
    ┌──────────────┐              ┌──────────────────┐
    │   APPROVED   │ (Terminal)   │     REJECTED     │ (Terminal)
    └──────────────┘              └──────────────────┘
```

### Transition Matrix:
* `PENDING_HUMAN_REVIEW` $\to$ `IN_REVIEW`, `APPROVED`, `REJECTED`, `REVISION_REQUESTED`
* `IN_REVIEW` $\to$ `APPROVED`, `REJECTED`, `REVISION_REQUESTED`, `PENDING_HUMAN_REVIEW`
* `REVISION_REQUESTED` $\to$ `IN_REVIEW`, `APPROVED`, `REJECTED`, `PENDING_HUMAN_REVIEW`
* `APPROVED` $\to$ *Terminal (Immutable)*
* `REJECTED` $\to$ *Terminal (Immutable)*

---

## 3. Database Schema

### `inspection_reviews` Table
* `review_id` (VARCHAR(64), Primary Key)
* `inspection_id` (VARCHAR(64), Indexed)
* `component_id` (VARCHAR(64), Foreign Key to `components.component_id`, Indexed)
* `assessment_id` (VARCHAR(64), Indexed)
* `status` (VARCHAR(32), Indexed, Default: `"PENDING_HUMAN_REVIEW"`)
* `priority` (VARCHAR(32), Indexed)
* `reviewer_id` (VARCHAR(64), Nullable)
* `reviewer_name` (VARCHAR(128), Nullable)
* `reviewer_comments` (TEXT, Nullable)
* `original_vision_evidence` (JSON, Immutable snapshot)
* `original_decision` (JSON, Immutable snapshot)
* `original_assessment` (JSON, Immutable snapshot)
* `original_draft_work_order` (JSON, Immutable snapshot)
* `edited_work_order` (JSON, Nullable, stores human modifications)
* `reasoning_trace` (JSON, Immutable snapshot)
* `created_at` (TIMESTAMPTZ, Auto-generated)
* `updated_at` (TIMESTAMPTZ, Auto-updated)
* `reviewed_at` (TIMESTAMPTZ, Nullable)

### `review_audit_logs` Table
* `audit_id` (VARCHAR(64), Primary Key)
* `review_id` (VARCHAR(64), Foreign Key to `inspection_reviews.review_id`, Indexed)
* `event_type` (VARCHAR(64), Indexed)
* `reviewer_id` (VARCHAR(64), Nullable)
* `reviewer_name` (VARCHAR(128), Nullable)
* `previous_status` (VARCHAR(32), Nullable)
* `new_status` (VARCHAR(32), Nullable)
* `change_summary` (TEXT, Nullable)
* `metadata_snapshot` (JSON, Nullable)
* `created_at` (TIMESTAMPTZ, Auto-generated)

---

## 4. REST API Endpoints

| HTTP Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/reviews` | List reviews with status, priority, and component filters |
| `POST` | `/api/v1/reviews` | Initialize review from `AgentInspectionAssessment` |
| `GET` | `/api/v1/reviews/{review_id}` | Retrieve complete review details and audit logs |
| `PUT` | `/api/v1/reviews/{review_id}` | Update reviewer notes or edit draft work order |
| `POST` | `/api/v1/reviews/{review_id}/approve` | Explicit inspector authorization (`APPROVED`) |
| `POST` | `/api/v1/reviews/{review_id}/reject` | Explicit inspector rejection (`REJECTED`) |
| `POST` | `/api/v1/reviews/{review_id}/request-revision` | Request supplementary NDE or revised data |
| `GET` | `/api/v1/reviews/{review_id}/audit` | Retrieve chronological, immutable audit history |
| `GET` | `/api/v1/images/raw/{filename}` | Stream original RGB inspection image |
| `GET` | `/api/v1/images/overlay/{filename}` | Stream segmentation mask overlay image |

---

## 5. Human-in-the-Loop Safety Controls
1. **No Automatic Work-Order Approval**: All AI generated work orders are created as `PENDING_HUMAN_REVIEW`.
2. **Zero External CMMS Dispatch**: Work order approval updates PostgreSQL database state only; no external emails, SMS, or CMMS dispatch jobs are triggered.
3. **Immutability of Perception Evidence**: The original `VisionEvidence`, `InspectionDecision`, and `AgentInspectionAssessment` JSON blobs are preserved immutably in `original_*` columns.
4. **Attributed Audit Trail**: Every status change or draft modification requires inspector identification (`reviewer_id`, `reviewer_name`) and records timestamps in `review_audit_logs`.

---

## 6. Frontend Dashboard
Accessible at `http://localhost:8000/dashboard`:
- **Inspection Queue**: Real-time list with status/priority filtering and search.
- **Visual Evidence Workspace**: Interactive toggle between raw RGB image and AI segmentation overlay, with live metric tiles (defect count, Laplacian sharpness, confidence).
- **Physical Detections Breakdown**: Table of individual crack contours, confidence scores, and affected area percentages.
- **Multi-Modal Reasoning Tab**: LLM summary, historical context citations, mechanical engineering reasoning narrative, risk factors, and explicit uncertainties.
- **Work Order Editor Tab**: Inline editable form for priority, assigned team, procedure, justification, required NDE method, estimated downtime, and estimated cost.
- **Action Modal**: Mandatory reviewer comment capture for Approve, Reject, and Request Revision workflows.
- **Audit Trail Tab**: Visual timeline of all lifecycle events.
