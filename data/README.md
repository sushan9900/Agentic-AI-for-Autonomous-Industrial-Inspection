# Data Directory Management

This directory structures the data lifecycle for the **Agentic AI for Autonomous Industrial Inspection** platform.

## Directory Layout
```text
data/
├── raw/                      # Original source datasets (untouched)
│   ├── pipeline_corrosion/   # Mendeley Pipeline Corrosion dataset
│   ├── corrosion_condition/  # Mendeley Corrosion Condition dataset
│   ├── deepcrack/            # DeepCrack dataset
│   └── mvtec_ad/             # MVTec AD benchmark dataset
├── processed/                # Unified and normalized training datasets
│   ├── coco/                 # Master COCO JSON datasets
│   └── yolo/                 # YOLO format training/val/test splits
└── sample/                   # Lightweight sample imagery for smoke tests
```

## Security & Version Control
All data folders (`data/raw/*`, `data/processed/*`) are excluded from Git version control via `.gitignore`.
Only directory `.gitkeep` markers and documentation READMEs are tracked.
