# DeepCrack Benchmark Dataset

**Repository:** [https://github.com/yhlleo/DeepCrack](https://github.com/yhlleo/DeepCrack)  
**Paper Reference:** Liu et al., *"DeepCrack: A Deep Hierarchical Feature Learning Architecture for Crack Segmentation"*, Neurocomputing, 2019. [DOI: 10.1016/j.neucom.2019.01.036](https://doi.org/10.1016/j.neucom.2019.01.036)  
**License / Terms:** Restricted to non-commercial research and educational use.

---

## 1. Archive & Acquisition Details
- **Acquired Archive:** `DeepCrack.zip` (67,708,808 bytes, ~64.57 MB)
- **SHA-256 Checksum:** `ec3fc2bee3b71c2cc3c74739cbc51c97b77f78193d08ce3dda0e16d7d41bf585`
- **Integrity:** Passed `zipfile.testzip()` (1,079 entries).
- **Extracted Location:** `data/raw/deepcrack/extracted/`

---

## 2. Directory & Split Structure
```text
data/raw/deepcrack/
├── DeepCrack.zip                 # Untouched original ZIP archive (64.57 MB)
├── dataset_manifest.json         # Machine-readable factual metadata manifest
├── INSPECTION_REPORT.md          # Comprehensive dataset inspection report
├── README.md                     # Dataset documentation
└── extracted/
    ├── train_img/                # 300 training RGB JPEG images
    ├── train_lab/                # 300 training binary PNG crack masks
    ├── test_img/                 # 237 testing RGB JPEG images
    └── test_lab/                 # 237 testing binary PNG crack masks
```

---

## 3. Dataset Summary
- **Total Images:** 537 RGB images (300 Train, 237 Test).
- **Total Masks:** 537 binary segmentation masks (300 Train, 237 Test).
- **Pairing:** 100% paired (0 missing, 0 orphan masks).
- **Resolutions:** Standardized: 490 images are $544 \times 384$ px; 47 images are $384 \times 544$ px.
- **Mask Encoding:** Pixel value 0 = background, 255 = crack foreground.
