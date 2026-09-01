# Image-based Corrosion Detection Dataset

**DOI:** [10.17632/tbjn6p2gn9.1](https://doi.org/10.17632/tbjn6p2gn9.1)  
**Authors:** Mohammad R. Jahanshahi, Deegan Atha, Cheng Qian (2020)  
**Publisher:** Mendeley Data  
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)  
**Associated Research:** Atha & Jahanshahi (2018), *"Evaluation of deep learning approaches based on convolutional neural networks for corrosion detection"*, Computer-Aided Civil and Infrastructure Engineering.

---

## 1. Archive & Acquisition Details
- **Original Archive:** `Corrosion_Data.zip` (662,667,730 bytes)
- **SHA-256 Checksum:** `f667aedcb6be8e25bdd3a454d106f9304953ad4eb5f267f6798b228be397c07a`
- **Integrity Status:** Verified via SHA-256 and `zipfile.testzip()`.
- **Extraction Location:** `data/raw/corrosion_detection/extracted/`

---

## 2. Directory & File Structure
```text
data/raw/corrosion_detection/
├── Corrosion_Data.zip            # Original untouched ZIP archive
├── dataset_manifest.json         # Machine-readable factual metadata manifest
├── INSPECTION_REPORT.md          # Comprehensive data inspection & analysis report
├── README.md                     # Dataset documentation
└── extracted/                    # Safe extracted archive contents
    └── Largeimage/               # Directory containing 152 full-scale JPEG images
        ├── 000001.jpg
        ├── 000004.jpg
        └── ... (152 total .jpg files)
```

---

## 3. Dataset Summary
- **Image Count:** 152 high-resolution RGB JPEG images.
- **Corrupted Images:** 0.
- **Duplicate Images:** 0.
- **Resolution Range:** Widths: 1704px – 8192px (median: 3024px); Heights: 1114px – 5461px (median: 3024px).
- **Annotation Format:** No external bounding box or mask files are bundled in this source archive (raw full-scale source captures).
- **Splits:** Official train/val/test splits were not provided within the raw source archive.
