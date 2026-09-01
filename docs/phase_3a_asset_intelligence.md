# Phase 3A: Inspection History & Operational Analytics

## 1. Overview & Architecture
Phase 3A transforms the platform into an **Asset-Aware Historical Inspection & Operational Analytics Platform**.

The system enables fleet-wide tracking of physical industrial assets (e.g. `PIPE-001`, `TANK-004`, `STRUCT-012`, `PUMP-007`), normalized defect telemetry over time, deterministic mathematical trend analysis, explainable operational risk scoring, and unified chronological lifecycle timelines.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      FLEET / ASSET LEVEL INTELLIGENCE                  │
├────────────────────────────────────────────────────────────────────────┤
│ • Assets Table (Primary Physical Asset Identity)                       │
│ • DefectRecords (Normalized Physical Telemetry & Geometry)             │
│ • HistoryService & TrendService (Mathematical Slopes & Recurrence)     │
│ • RiskService (Deterministic & Explainable Operational Risk Scores)    │
│ • TimelineService (Unified Chronological Lifecycle Aggregation)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│   REST API (/api/v1/assets,     │           │   ASSET INTELLIGENCE HUB (UI)   │
│   /api/v1/analytics)            │           │   (Dynamic Charts & Timeline)   │
└─────────────────────────────────┘           └─────────────────────────────────┘
```

---

## 2. Database Schema & Normalized Telemetry

### `defect_records` Table
* `id` (INTEGER, Primary Key, Auto-increment)
* `defect_id` (VARCHAR(64), Unique, Indexed)
* `inspection_id` (VARCHAR(64), Indexed)
* `asset_id` (VARCHAR(64), Foreign Key to `assets.asset_id`, Indexed)
* `component_id` (VARCHAR(64), Foreign Key to `components.component_id`, Indexed)
* `defect_type` (VARCHAR(64), Indexed)
* `confidence` (FLOAT, Detection probability)
* `affected_area_percentage` (FLOAT, Surface area %)
* `bounding_box_area_percentage` (FLOAT)
* `crack_length_pixels` (FLOAT, Linear extent)
* `crack_width_estimate_pixels` (FLOAT)
* `location_type` (VARCHAR(64), Geometric placement)
* `detection_timestamp` (TIMESTAMPTZ, Indexed)
* `raw_evidence_detection_id` (VARCHAR(64), Traceability link)
* `source_type` (VARCHAR(64), Provenance)

### Indexes for High-Performance Queries
* `ix_defect_records_asset_time`: `(asset_id, detection_timestamp)`
* `ix_defect_records_type_time`: `(defect_type, detection_timestamp)`
* `ix_inspection_reviews_asset_status`: `(asset_id, status)`
* `ix_assets_asset_code`: `(asset_code)`

---

## 3. Deterministic Analytics & Operational Risk

### A. Mathematical Trend Calculations (`TrendService`)
* **Defect Count Trend**: Compares defect detection density across sequential halves of the inspection time series (`INCREASING`, `DECREASING`, `STABLE`).
* **Area Severity Trend**: Evaluates surface defect expansion (`EXPANDING`, `STABLE`, `RESOLVED`).
* **Inspection Frequency**: Calculates average days between recorded inspection transactions.

### B. Explainable Operational Risk Scoring (`RiskService`)
Deterministic formula mapping operational factors to a 0–100 score:
- **Base Baseline**: 10
- **Inspection Recency**: +20 if overdue (> 365 days), +10 if interval exceeded (> 180 days), +25 if no baseline exists.
- **Defect Count & Severity**: +5 per defect (max +25), +20 for recurrence across $\ge 2$ inspections, +15 for high affected area ($\ge 4.0\%$), +10 for linear crack length ($\ge 200\text{px}$).
- **Unresolved Work Orders**: +25 if CRITICAL work orders pending, +15 for active open work orders.

**Risk Bands:**
* $\ge 75$: `CRITICAL`
* $50 - 74$: `HIGH`
* $25 - 49$: `MEDIUM`
* $< 25$: `LOW`

> [!IMPORTANT]
> **Safety Notice**: The operational risk score is an explainable analytics indicator. It is explicitly labeled: *"AI-assisted operational risk indicator — human engineering review required."*

---

## 4. REST API Endpoints

### Asset Management & Intelligence (`/api/v1/assets`)
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/assets` | List assets with risk scores, recency, and filters |
| `POST` | `/api/v1/assets` | Register new industrial asset |
| `GET` | `/api/v1/assets/{asset_id}` | Get asset specifications, components, and risk summary |
| `PUT` | `/api/v1/assets/{asset_id}` | Update asset metadata |
| `GET` | `/api/v1/assets/{asset_id}/inspections` | Inspection history with date-range filters |
| `GET` | `/api/v1/assets/{asset_id}/defects` | Normalized defect records |
| `GET` | `/api/v1/assets/{asset_id}/risk` | Explainable operational risk snapshot |
| `GET` | `/api/v1/assets/{asset_id}/trends` | Time-series trend metrics |
| `GET` | `/api/v1/assets/{asset_id}/work-orders` | Associated work orders |
| `GET` | `/api/v1/assets/{asset_id}/timeline` | Unified chronological lifecycle timeline |

### Fleet Analytics (`/api/v1/analytics`)
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/analytics/overview` | High-level fleet metrics (assets, defects, open reviews, risk) |
| `GET` | `/api/v1/analytics/defects` | Defect distributions by type and top affected assets |
| `GET` | `/api/v1/analytics/risk` | Fleet risk-band distribution and prioritized high-risk queue |
