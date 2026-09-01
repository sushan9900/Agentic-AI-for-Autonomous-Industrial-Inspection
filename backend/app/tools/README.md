# Agent Tools Repository (`backend/app/tools`)

Structured, strongly typed tools executable by autonomous agent workflows.

## Tools Directory
1. **`get_asset_context`** ([asset_context.py](file:///c:/sushan_repos/Agentic-AI-for-Autonomous-Industrial-Inspection/backend/app/tools/asset_context.py)): Queries PostgreSQL for physical asset specifications, age, operational status, and sub-components.
2. **`get_maintenance_history`** ([maintenance_history.py](file:///c:/sushan_repos/Agentic-AI-for-Autonomous-Industrial-Inspection/backend/app/tools/maintenance_history.py)): Retrieves chronological past repairs, downtime, actual costs, and technician notes.
3. **`get_severity_thresholds`** ([severity_thresholds.py](file:///c:/sushan_repos/Agentic-AI-for-Autonomous-Industrial-Inspection/backend/app/tools/severity_thresholds.py)): Queries deterministic project-defined engineering threshold rules (`source_type="project_defined_rule"`).
4. **`check_similar_incidents`** ([similar_incidents.py](file:///c:/sushan_repos/Agentic-AI-for-Autonomous-Industrial-Inspection/backend/app/tools/similar_incidents.py)): Retrieves matching historical facility failure incidents and corrective actions.
5. **`calculate_risk_score`** ([risk_scoring.py](file:///c:/sushan_repos/Agentic-AI-for-Autonomous-Industrial-Inspection/backend/app/tools/risk_scoring.py)): Computes a reproducible, explainable 0–100 operational risk index.
