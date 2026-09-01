# Comprehensive Benchmark Inspection Report: MVTec Anomaly Detection (MVTec AD)

**Official Source:** `https://www.mvtec.com/research-teaching/datasets/mvtec-ad`  
**Paper Reference:** Bergmann et al., *"MVTec AD — A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection"*, CVPR 2019 / IJCV 2021  
**DOI:** 10.1007/s11263-020-01400-4  
**Inspection Date:** 2026-08-31  

---

## 1. Source Verification
* **Official Publisher:** MVTec Software GmbH `[FACT]`
* **Official URL:** `https://www.mvtec.com/research-teaching/datasets/mvtec-ad` `[FACT]`
* **Evaluation Package URL:** `https://www.mydrive.ch/shares/150450/bb24b914a28ddd2b5e35bd53d23177cd/download/439517473-1665675012/mvtec_ad_evaluation.tar.xz` `[FACT]`

---

## 2. License
* **Terms:** **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)** `[FACT]`
* **Use Restrictions:** Non-commercial research, academic, and evaluation purposes `[FACT]`

---

## 3. Acquisition
* **Evaluation Package:** Acquired `mvtec_ad_evaluation.tar.xz` (11,056 bytes, SHA-256: `dfcda7d67eee25316ec6ae5042c0b1684a4cabf33b2346be351e2ce36013f220`) into `data/raw/mvtec_ad/evaluation/` `[FACT]`
* **Isolation Guarantee:** MVTec AD is preserved as a separate unsupervised benchmark; no files are merged into `corrosion_detection`, `corrosion_segmentation`, or `deepcrack` `[FACT]`

---

## 4. Archive & Package Verification
* **Evaluation Code Archive:** `mvtec_ad_evaluation.tar.xz` verified and extracted with 0 corruptions `[FACT]`
* **Contents:** PRO curve integration tools (`pro_curve_util.py`), ROC curve metrics (`roc_curve_util.py`), and experiment runners (`evaluate_experiment.py`) `[FACT]`

---

## 5. Dataset Structure
Each category adheres to the strict unsupervised anomaly detection hierarchy:
```text
<category_name>/
├── train/
│   └── good/                     # Defect-free normal training images
├── test/
│   ├── good/                     # Defect-free normal test images
│   ├── <defect_type_1>/          # Anomalous test captures
│   └── <defect_type_2>/
└── ground_truth/
    ├── <defect_type_1>/          # Pixel-accurate binary PNG anomaly masks
    └── <defect_type_2>/
```
* **Decoupled Architecture:** Defect categories and structures are independent per object/texture `[FACT]`

---

## 6. Category Inventory
* **Total Categories:** 15 (5 textures, 10 objects) `[FACT]`
* **Texture Categories (5):** `carpet`, `grid`, `leather`, `tile`, `wood` `[FACT]`
* **Object Categories (10):** `bottle`, `cable`, `capsule`, `hazelnut`, `metal_nut`, `pill`, `screw`, `toothbrush`, `transistor`, `zipper` `[FACT]`
* **No Taxonomy Forcing:** MVTec categories remain strictly untouched and are NOT mapped into the project's 4-class supervised taxonomy `[FACT]`

---

## 7. Training Data Analysis
* **Total Training Images:** 3,629 images `[FACT]`
* **Defect Status:** **100% normal / defect-free** (`train/good/`) `[FACT]`
* **Purpose:** Enables unsupervised one-class density estimation / deep feature memory bank construction `[INFERENCE]`

---

## 8. Test Data Analysis
* **Total Test Images:** 1,725 images `[FACT]`
* **Normal Test Images:** 467 images (`test/good/`) `[FACT]`
* **Anomalous Test Images:** 1,258 images containing real defects across 73 anomaly types `[FACT]`

---

## 9. Ground-Truth Masks
* **Total Masks:** 1,258 binary PNG masks `[FACT]`
* **Resolution:** Exact pixel match with corresponding anomalous test images `[FACT]`
* **Pixel Values:** `0` for background/normal regions, `255` for pixel anomalies `[FACT]`

---

## 10. Anomaly Taxonomy (73 Defect Types across 15 Categories)
* **`bottle`:** `broken_large`, `broken_small`, `contamination`
* **`cable`:** `bent_wire`, `cable_swap`, `combined`, `cut_inner_insulation`, `cut_outer_insulation`, `missing_cable`, `missing_wire`, `poke_insulation`
* **`capsule`:** `crack`, `faulty_imprint`, `poke`, `scratch`, `squeeze`
* **`carpet`:** `color`, `cut`, `hole`, `metal_contamination`, `thread`
* **`grid`:** `bent`, `broken`, `glue`, `metal_contamination`, `thread`
* **`hazelnut`:** `crack`, `cut`, `hole`, `print`
* **`leather`:** `color`, `cut`, `fold`, `glue`, `poke`
* **`metal_nut`:** `bent`, `color`, `flip`, `scratch`
* **`pill`:** `color`, `combined`, `contamination`, `crack`, `faulty_imprint`, `pill_type`, `scratch`
* **`screw`:** `manipulated_front`, `scratch_head`, `scratch_neck`, `thread_side`, `thread_top`
* **`tile`:** `crack`, `glue_strip`, `gray_stroke`, `oil`, `rough`
* **`toothbrush`:** `defective`
* **`transistor`:** `bent_lead`, `cut_lead`, `damaged_case`, `misplaced`
* **`wood`:** `color`, `combined`, `hole`, `liquid`, `scratch`
* **`zipper`:** `broken_teeth`, `combined`, `fabric_border`, `fabric_interior`, `rough`, `split_teeth`, `squeezed_teeth` `[FACT]`

---

## 11. Data-Quality Findings
* **Positive:** Gold-standard real-world industrial inspection benchmark with controlled illumination, diverse defect modalities, and exact pixel annotations `[OBSERVATION]`.
* **Zero Leakage:** Training sets are strictly defect-free; test sets contain balanced normal and anomalous samples `[FACT]`.

---

## 12. Duplicate / Leakage Analysis
* **Structure:** Zero leakage between training and testing sets by formal benchmark design `[FACT]`.

---

## 13. PatchCore Suitability
* **Suitability:** **100% Ideal / Primary Benchmark Target** `[RECOMMENDATION]`.
* **Alignment:**
  * PatchCore trains its memory bank strictly on `train/good/` features.
  * Evaluates anomaly scores against `test/good/` and `test/<defect>/`.
  * Computes AU-PRO and pixel AUROC directly against `ground_truth/` masks using official evaluation scripts in `data/raw/mvtec_ad/evaluation/` `[RECOMMENDATION]`.

---

## 14. Limitations
1. Not suitable for supervised multi-class bounding box detection (e.g. YOLO).
2. Restricted to non-commercial research under CC BY-NC-SA 4.0. `[FACT]`

---

## 15. Recommended Role in Project
1. **Unsupervised Anomaly Baseline:** Serve exclusively as the validation benchmark for PatchCore unsupervised anomaly detection in later phases `[RECOMMENDATION]`.
2. **Evaluation Metrics:** Utilize the official MVTec evaluation scripts (`evaluate_experiment.py`, `pro_curve_util.py`) for AUROC and PRO reporting `[RECOMMENDATION]`.
