# Comprehensive Dataset Inspection Report: Image-based Corrosion Detection Dataset

**Dataset DOI:** 10.17632/tbjn6p2gn9.1  
**Publisher / Source:** Mendeley Data (Jahanshahi, Atha & Qian, 2020)  
**Inspection Date:** 2026-08-31  

---

## 1. Archive Verification
* **Archive Path:** `data/raw/corrosion_detection/Corrosion_Data.zip` `[FACT]`
* **File Size:** `662,667,730` bytes (~631.97 MB) `[FACT]`
* **SHA-256 Checksum:** `f667aedcb6be8e25bdd3a454d106f9304953ad4eb5f267f6798b228be397c07a` `[FACT]`
* **Checksum Status:** Matches official Mendeley Data content hash `[FACT]`
* **ZIP Structure Verification:** `zipfile.testzip()` passed with 0 corrupt members across 152 entries `[FACT]`

---

## 2. Extraction Status
* **Extraction Directory:** `data/raw/corrosion_detection/extracted/` `[FACT]`
* **Path Traversal Security:** All archive entries validated against relative/absolute path traversal before extraction `[FACT]`
* **Original Archive Status:** `Corrosion_Data.zip` remains completely unmodified and preserved `[FACT]`

---

## 3. Directory Structure
```text
data/raw/corrosion_detection/extracted/
└── Largeimage/
    ├── 000001.jpg
    ├── 000004.jpg
    ├── ...
    └── 000597.jpg
```
* **Total Directories:** 1 (`Largeimage/`) `[FACT]`
* **Total Files:** 152 `[FACT]`

---

## 4. File Inventory
* **Total Files:** 152 `[FACT]`
* **Image Files:** 152 (100% `.jpg`) `[FACT]`
* **Annotation Files:** 0 bundled in archive `[FACT]`
* **Metadata / Documentation Files:** 0 bundled in archive `[FACT]`

---

## 5. Image Statistics
* **Total Image Count:** 152 `[FACT]`
* **Readable Images:** 152 (100%) `[FACT]`
* **Corrupted Images:** 0 `[FACT]`
* **Color Channels:** 3-channel RGB (152 / 152 images) `[FACT]`
* **Image Width Range:**
  * Minimum: 1,704 px
  * Maximum: 8,192 px
  * Median: 3,024 px `[FACT]`
* **Image Height Range:**
  * Minimum: 1,114 px
  * Maximum: 5,461 px
  * Median: 3,024 px `[FACT]`
* **Most Common Resolutions:**
  1. `3024 × 4032`: 31 images (20.39%)
  2. `3024 × 3024`: 29 images (19.08%)
  3. `2592 × 1944`: 25 images (16.45%)
  4. `5820 × 3880`: 5 images (3.29%)
  5. `5184 × 3456`: 4 images (2.63%) `[FACT]`

---

## 6. Annotation Statistics
* **Native Annotation Format:** None bundled in source archive `[FACT]`
* **Total Native Annotations:** 0 `[FACT]`
* **Annotation/Image Pairing:** N/A (Image-only repository) `[FACT]`

---

## 7. Original Label Inventory
* **Provided Category:** `corrosion` (implied by dataset title and associated research publication) `[FACT]`
* **Sub-classes Provided:** None in raw archive `[FACT]`

---

## 8. Bounding-Box Findings
* **Bounding Boxes Present in Archive:** 0 `[FACT]`
* **Status:** No pre-annotated bounding boxes were shipped with this specific archive `[FACT]`

---

## 9. Segmentation Findings
* **Segmentation Masks Present in Archive:** 0 `[FACT]`
* **Status:** No pre-annotated pixel masks or polygon JSON files were shipped with this specific archive `[FACT]`

---

## 10. Dataset Split Findings
* **Official Splits:** Official train/val/test split not found in source archive `[FACT]`

---

## 11. Duplicate Findings
* **Identical SHA-256 File Hashes:** 0 duplicate images found across the 152 image captures `[FACT]`
* **Sequences / Continuity:** Filenames span from `000001.jpg` to `000597.jpg` with non-contiguous gaps, indicating selective curation of distinct corrosion scenes rather than raw consecutive video frames `[OBSERVATION]`

---

## 12. Domain Observations
* **Visual Content:** Real-world civil and industrial structural steel, piping, girders, metal plates, and equipment exhibiting heavy oxidation, flaking paint, and surface rust `[OBSERVATION]`
* **Lighting & Environment:** Natural outdoor daylight, variable shadows, weathering, and complex realistic industrial backgrounds `[OBSERVATION]`
* **Domain Specificity:** While containing significant piping and industrial structural steel, it is a broad structural/metal corrosion dataset rather than strictly a dedicated transmission pipeline dataset `[OBSERVATION]`

---

## 13. Data-Quality Problems
* **High Image Quality:** Extremely high resolution (many >12 megapixels) with sharp visual texture and rich color information `[OBSERVATION]`
* **Annotation Absence:** Because no external bounding boxes or segmentation masks are included in `Corrosion_Data.zip`, this archive cannot be directly converted to YOLO/COCO bounding boxes without secondary annotation or patch generation `[INFERENCE]`

---

## 14. Potential Use for YOLO Detection
* **Suitability:** High for pretraining / fine-tuning if sliced into high-resolution patches or annotated, but requires paired bounding box labels `[INFERENCE]`

---

## 15. Potential Use for YOLO Segmentation
* **Suitability:** High potential for generating polygon segmentations given the high resolution and distinct boundary contrast of the corrosion patches `[INFERENCE]`

---

## 16. Limitations
1. Limited dataset sample count (152 high-resolution master images).
2. Absence of bundled bounding box / polygon annotation files.
3. No pre-established train/test splits. `[FACT]`

---

## 17. Recommendations
1. **Preserve Raw State:** Keep `data/raw/corrosion_detection/extracted/Largeimage/` strictly untouched as the ground-truth raw visual repository `[RECOMMENDATION]`.
2. **Combine with Annotated Secondary Datasets:** In subsequent phases, pair this high-resolution raw corrosion imagery with datasets containing pre-annotated bounding boxes and segmentation masks (e.g. DeepCrack, COCO-formatted structural corrosion sets) `[RECOMMENDATION]`.
3. **Patch Slicing Strategy:** When preparing for YOLO11 training, utilize standard sliding window tile extraction (e.g. $640 \times 640$ patches) to expand these 152 ultra-high-resolution images into several thousand standard-size training samples `[RECOMMENDATION]`.
