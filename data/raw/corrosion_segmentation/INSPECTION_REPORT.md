# Comprehensive Dataset Inspection Report: Images and Pixel Annotations for Corrosion Segmentation

**Dataset DOI:** 10.17632/kcyn4nhv2c.1  
**Publisher / Source:** Mendeley Data (Rios, Netto & Roehl / PUC-Rio, 2023)  
**Inspection Date:** 2026-08-31  

---

## 1. Source Verification
* **DOI:** `10.17632/kcyn4nhv2c.1` (Resolves to Mendeley Data, confirmed in DataCite registry) `[FACT]`
* **Title:** *Images and pixel annotations for corrosion segmentation* `[FACT]`
* **Authors:** Marina Rios, Paulo Ivson Netto, Deane Roehl (PUC-Rio) `[FACT]`
* **License:** Creative Commons Attribution 4.0 International (CC BY 4.0) `[FACT]`

---

## 2. Acquisition
* **Acquisition Method:** Resumable streaming download directly from Mendeley Data S3 backend `[FACT]`
* **Acquired Archive:** `Labeled images.zip` `[FACT]`
* **Target Storage:** `data/raw/corrosion_segmentation/` `[FACT]`

---

## 3. Archive Verification
* **File Size:** `262,967,506` bytes (~250.78 MB) `[FACT]`
* **SHA-256 Checksum:** `6fbd29524a81f4d8250a3cf978da09ad09d48f65522677792156d0bdf454fcce` `[FACT]`
* **Integrity Status:** Verified with `zipfile.testzip()` (151 archive entries, 0 corrupted) `[FACT]`

---

## 4. Extraction Status
* **Extraction Path:** `data/raw/corrosion_segmentation/extracted/Labeled images/` `[FACT]`
* **Security Checks:** All member paths validated against directory traversal (`../`, absolute paths) prior to unzipping `[FACT]`
* **Source Preservation:** Original archive `Labeled images.zip` preserved untouched `[FACT]`

---

## 5. File & Directory Structure
```text
data/raw/corrosion_segmentation/
├── Labeled images.zip
├── dataset_manifest.json
├── INSPECTION_REPORT.md
├── README.md
└── extracted/
    └── Labeled images/
        └── Labeled images/
            ├── Original images/          # 34 original high-res TIFF captures
            ├── Label visualization/      # 36 visualization TIFFs showing patch selections
            └── Labels/
                ├── Corrosion/            # 35 .tif.zip archives containing ImageJ .roi files
                └── Background/           # 35 .tif.zip archives containing ImageJ .roi files
```
* **Total Files:** 145 files (34 original TIFFs, 36 visualization TIFFs, 70 label ZIPs, 5 desktop.ini files) `[FACT]`

---

## 6. Image Statistics
* **Total Original Images:** 34 `[FACT]`
* **Readable Images:** 34 (100%) `[FACT]`
* **Corrupted Images:** 0 `[FACT]`
* **Format:** Uncompressed TIFF (.tif) `[FACT]`
* **Color Channels:** 3-channel RGB `[FACT]`
* **Width Range:** Min = `200 px`, Max = `3,952 px`, Median = `1,581 px` `[FACT]`
* **Height Range:** Min = `132 px`, Max = `3,380 px`, Median = `956 px` `[FACT]`

---

## 7. Annotation Structure
* **Format:** ImageJ binary Region of Interest (`.roi`) files of 146 bytes each, packed into `.tif.zip` containers `[FACT]`
* **Total Corrosion Label ZIPs:** 35 archives containing 352 individual `.roi` files `[FACT]`
* **Total Background Label ZIPs:** 35 archives containing 351 individual `.roi` files `[FACT]`
* **Total Sparse Annotations:** 703 coordinate patches across the dataset `[FACT]`

---

## 8. Mask Statistics & Nature of Annotations
* **Full-Resolution Dense Binary Masks:** **0 (None)** `[FACT]`
* **Polygon Contours:** **0 (None)** `[FACT]`
* **Annotation Nature:** **Sparse Patch-Level Pixel Annotations**. The `.roi` files represent localized small coordinate bounding windows (sampling local pixel clusters of corrosion vs. uncorroded background) `[FACT]`.

---

## 9. Original Labels
* **Classes:**
  1. `Corrosion` (352 patch ROIs across 35 image cases)
  2. `Background` (351 patch ROIs across 35 image cases) `[FACT]`

---

## 10. Image/Annotation Pairing
* 34 original images in `Original images/` map to 35 corresponding label archives in `Labels/Corrosion/` and `Labels/Background/` (one image index `Imag26.tif` has multiple capture sub-variations) `[FACT]`.

---

## 11. Dataset Splits
* **Status:** Official train/validation/test split not found in source archive `[FACT]`.

---

## 12. Duplicate Analysis
* **Image Duplicates:** All 34 original TIFF images possess distinct SHA-256 hashes `[FACT]`.

---

## 13. Domain Observations
* **Visual Content:** Field captures of atmospheric corrosion on steel infrastructure, painted equipment, maritime assets, and outdoor metal fixtures `[OBSERVATION]`.
* **Lighting & Textures:** High variance in illumination, paint flaking, blistered protective coatings, and raw rust texture `[OBSERVATION]`.
* **Domain Specificity:** General industrial atmospheric corrosion; contains piping and structural components but is not limited exclusively to pipeline geometries `[OBSERVATION]`.

---

## 14. Data-Quality Findings
* **Positive:** Clear, realistic field captures of corrosion texture and coating degradation `[OBSERVATION]`.
* **Critical Finding:** Because annotations are **sparse ImageJ coordinate patches** (used for pixel classifier feature extraction) rather than full object bounding boxes or dense instance segmentation polygons, this dataset **cannot directly train YOLO11-Seg out-of-the-box** without extensive manual mask annotation or pseudo-mask generation `[INFERENCE]`.

---

## 15. Suitability for YOLO Detection
* **Suitability:** **Low / Inappropriate**. The 703 patches are microscopic local coordinate samples ($20 \times 20$ px windows) rather than component-level object bounding boxes `[RECOMMENDATION]`.

---

## 16. Suitability for YOLO Segmentation
* **Suitability:** **Low / Inappropriate**. YOLO11-Seg requires full boundary polygon masks enclosing each defect instance; sparse ImageJ point patches do not satisfy YOLO segmentation contracts `[RECOMMENDATION]`.

---

## 17. Suitability for Other Segmentation Methods
* **Suitability:** **High** for patch-based pixel classifiers, classical texture segmentation (Random Forests / Gabor filters / k-means), or semantic feature clustering `[INFERENCE]`.

---

## 18. Limitations
1. Small image count (34 original images).
2. Annotations are sparse sampling patches rather than dense ground-truth masks.
3. Lack of full object boundary labels. `[FACT]`

---

## 19. Recommended Use in Our Project
1. **Use as a Pixel-Level Feature & Texture Benchmark:** Utilize the 703 labeled corrosion/background patches for validating local color/texture severity features in `vision/preprocessing/` `[RECOMMENDATION]`.
2. **Do NOT Use as Primary YOLO11-Seg Target:** Do not use this dataset as the primary instance segmentation dataset for training YOLO11-Seg. Instead, rely on datasets with full polygon annotations (e.g. DeepCrack, COCO-formatted structural defect datasets) `[RECOMMENDATION]`.
