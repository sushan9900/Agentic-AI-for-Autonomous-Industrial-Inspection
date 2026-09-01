# MVTec Anomaly Detection (MVTec AD) Benchmark

**Official Source:** [https://www.mvtec.com/research-teaching/datasets/mvtec-ad](https://www.mvtec.com/research-teaching/datasets/mvtec-ad)  
**Paper Reference:** Paul Bergmann, Michael Fauser, David Sattlegger, Carsten Steger. *"MVTec AD — A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection"*, CVPR 2019 / IJCV 2021. [DOI: 10.1007/s11263-020-01400-4](https://doi.org/10.1007/s11263-020-01400-4)  
**License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (**CC BY-NC-SA 4.0**).

---

## 1. Benchmark Purpose
MVTec AD is the industry standard benchmark for **unsupervised visual anomaly detection and localization** (e.g. PatchCore, PaDiM, SPADE).

It is intentionally decoupled from conventional supervised detection pipelines:
- **Training Set:** 100% defect-free / normal images (`train/good/`).
- **Testing Set:** Normal images (`test/good/`) + anomalous defect images (`test/<defect_type>/`).
- **Ground Truth:** Pixel-level binary ground-truth anomaly masks (`ground_truth/<defect_type>/<id>_mask.png`).

---

## 2. Directory & Benchmark Structure
```text
data/raw/mvtec_ad/
├── dataset_manifest.json         # Machine-readable benchmark manifest
├── INSPECTION_REPORT.md          # Comprehensive data inspection report
├── README.md                     # Documentation
├── evaluation/                   # Official MVTec evaluation scripts
│   └── mvtec_ad_evaluation/      # PRO curve, ROC curve, and evaluation utilities
└── extracted/                    # Category dataset roots (unsupervised anomaly format)
    ├── bottle/
    ├── cable/
    ├── capsule/
    ├── carpet/
    ├── grid/
    ├── hazelnut/
    ├── leather/
    ├── metal_nut/
    ├── pill/
    ├── screw/
    ├── tile/
    ├── toothbrush/
    ├── transistor/
    ├── wood/
    └── zipper/
```

---

## 3. Dataset Summary
- **Total Categories:** 15 (5 textures, 10 objects).
- **Total Images:** 5,354 high-resolution industrial images.
- **Training Images:** 3,629 normal images.
- **Testing Images:** 1,725 images (467 normal, 1,258 anomalous).
- **Ground-Truth Masks:** 1,258 binary PNG masks across 73 defect types.
