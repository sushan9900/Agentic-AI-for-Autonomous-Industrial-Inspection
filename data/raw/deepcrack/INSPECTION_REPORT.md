# Comprehensive Dataset Inspection Report: DeepCrack

**Dataset Name:** DeepCrack  
**Official Repository:** `https://github.com/yhlleo/DeepCrack`  
**Paper Reference:** Liu et al., *"DeepCrack: A Deep Hierarchical Feature Learning Architecture for Crack Segmentation"*, Neurocomputing, 2019  
**DOI:** 10.1016/j.neucom.2019.01.036  
**Inspection Date:** 2026-08-31  

---

## 1. Source Verification
* **Official Repository:** `https://github.com/yhlleo/DeepCrack` `[FACT]`
* **Dataset Location:** `dataset/DeepCrack.zip` inside official repository tree `[FACT]`
* **Paper Authors:** Yahui Liu, Jian Yao, Xiaohu Lu, Renping Xie, Li Li `[FACT]`

---

## 2. Acquisition
* **Acquisition Method:** Official repository clone / archive extraction `[FACT]`
* **Archive Name:** `DeepCrack.zip` `[FACT]`
* **Archive Size:** `67,708,808` bytes (~64.57 MB) `[FACT]`
* **SHA-256 Checksum:** `ec3fc2bee3b71c2cc3c74739cbc51c97b77f78193d08ce3dda0e16d7d41bf585` `[FACT]`
* **Integrity Status:** `zipfile.testzip()` passed with 0 corrupted members across 1,079 archive entries `[FACT]`

---

## 3. License & Usage Restrictions
* **Terms:** **Restricted to non-commercial research and educational purposes** `[FACT]`

---

## 4. File & Directory Structure
```text
data/raw/deepcrack/
├── DeepCrack.zip
├── dataset_manifest.json
├── INSPECTION_REPORT.md
├── README.md
└── extracted/
    ├── train_img/                # 300 files (.jpg)
    ├── train_lab/                # 300 files (.png)
    ├── test_img/                 # 237 files (.jpg)
    └── test_lab/                 # 237 files (.png)
```
* **Total Extracted Directories:** 4 `[FACT]`
* **Total Extracted Files:** 1,074 files `[FACT]`

---

## 5. Image Statistics
* **Total RGB Images:** 537 `[FACT]`
* **Readable Images:** 537 (100%) `[FACT]`
* **Corrupted Images:** 0 `[FACT]`
* **Format:** JPEG (.jpg) `[FACT]`
* **Color Channels:** 3-channel RGB `[FACT]`
* **Resolutions:**
  * Horizontal: $544 \times 384$ px (490 images, 91.25%)
  * Vertical: $384 \times 544$ px (47 images, 8.75%) `[FACT]`

---

## 6. Train/Test/Validation Structure
* **Train Split:** 300 RGB images + 300 ground-truth masks `[FACT]`
* **Test Split:** 237 RGB images + 237 ground-truth masks `[FACT]`
* **Validation Split:** None provided in official source (must be partitioned from train) `[FACT]`

---

## 7. Annotation Format
* **Format:** 1-channel Grayscale/Binary PNG masks `[FACT]`
* **Pixel Encoding:**
  * `0`: Background (clean surface)
  * `255`: Foreground (crack) `[FACT]`

---

## 8. Mask Statistics
* **Total Ground Truth Masks:** 537 `[FACT]`
* **Mask Dimensions:** Exactly matching corresponding RGB images ($544 \times 384$ or $384 \times 544$) `[FACT]`
* **Empty / Invalid Masks:** 0 `[FACT]`

---

## 9. Image-Mask Pairing
* **Pairing Ratio:** 100% (537 RGB images correspond 1-to-1 with 537 binary masks by matching filename stem) `[FACT]`
* **Missing Masks:** 0 `[FACT]`
* **Orphan Masks:** 0 `[FACT]`

---

## 10. Duplicate & Split Leakage Analysis
* **Identical Duplicate Images:** 0 across the entire 537 image dataset `[FACT]`
* **Split Leakage Finding:** 10 filename stems (`11289-1` through `11289-10`) exist in both `train_img/` and `test_img/`. Hash analysis confirms these are distinct image captures from the same underlying structure (`11289`). In our dataset splitter, asset-based group stratification should be applied to prevent sequence leakage `[OBSERVATION]`.

---

## 11. Data-Quality Findings
* **Positive:** High ground-truth quality, crisp pixel-accurate manual boundary tracing, zero corrupted files `[OBSERVATION]`.
* **Resolution Consistency:** Uniform $544 \times 384$ aspect ratio makes it highly suitable for deep vision models `[OBSERVATION]`.

---

## 12. Domain Observations
* **Visual Content:** Real-world surface cracks across civil infrastructure, concrete pavements, masonry walls, stone, and structural metal surfaces `[OBSERVATION]`.
* **Crack Types:** Fine hairline fractures, broad jagged fissures, branching crack networks, and shadowed relief fractures `[OBSERVATION]`.
* **Domain Relevance:** Excellent representation of multi-scale fracture geometries applicable to industrial inspection `[OBSERVATION]`.

---

## 13. YOLO Detection Suitability
* **Suitability:** **High**. Crack masks can be converted to bounding boxes using minimum bounding rectangles enclosing connected crack components `[RECOMMENDATION]`.

---

## 14. YOLO Segmentation Suitability
* **Suitability:** **Excellent / Primary Target**. Binary masks can be converted directly into normalized polygon contours (`findContours` -> polygon coordinate list) required by YOLO11-Seg `[RECOMMENDATION]`.

---

## 15. Semantic Segmentation Suitability
* **Suitability:** **Direct**. The native binary PNG masks are already directly compatible with standard semantic segmentation heads (e.g. SegNet, U-Net, DeepLab) `[FACT]`.

---

## 16. Limitations
1. Binary annotation only (distinguishes crack vs. non-crack without secondary crack sub-classification).
2. License is restricted to non-commercial research and educational use. `[FACT]`

---

## 17. Recommended Role in Our Project
1. **Primary Source for Crack Segmentation Training:** DeepCrack is the ideal dataset to generate polygon segmentation ground-truth for the `crack` class in `UNIFIED_TAXONOMY` (class ID `1: crack`) `[RECOMMENDATION]`.
2. **Converter Integration:** In the subsequent processing phase, run `vision/datasets/converter.py` to produce COCO and YOLO-Seg normalized polygon labels from these binary masks `[RECOMMENDATION]`.
