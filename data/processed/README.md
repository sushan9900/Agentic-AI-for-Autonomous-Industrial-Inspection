# Processed Datasets Directory

This directory stores normalized, unified inspection datasets generated from raw sources.

## Layout
- `coco/` — Master COCO JSON format datasets with canonical 4-class unified taxonomy (`0: corrosion`, `1: crack`, `2: coating_damage`, `3: surface_damage`).
- `yolo/` — Exported YOLO format training directories (`train/`, `val/`, `test/` with `images/` and `labels/`).

> [!IMPORTANT]
> **Git Exclusion**: Processed datasets and extracted training sets are strictly excluded from version control via `.gitignore`.
> **Phase 1C Status**: No processed dataset files have been generated.
