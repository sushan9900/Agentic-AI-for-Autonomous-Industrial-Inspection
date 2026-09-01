# Images and Pixel Annotations for Corrosion Segmentation

**DOI:** [10.17632/kcyn4nhv2c.1](https://doi.org/10.17632/kcyn4nhv2c.1)  
**Authors:** Marina Rios, Paulo Ivson Netto, Deane Roehl (PUC-Rio, 2023)  
**Publisher:** Mendeley Data  
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)  

---

## 1. Archive & Acquisition Details
- **Acquired Archive:** `Labeled images.zip` (262,967,506 bytes, ~250.78 MB)
- **SHA-256 Checksum:** `6fbd29524a81f4d8250a3cf978da09ad09d48f65522677792156d0bdf454fcce`
- **Integrity Status:** Verified via SHA-256 and `zipfile.testzip()` (151 archive entries).
- **Extraction Location:** `data/raw/corrosion_segmentation/extracted/Labeled images/`

---

## 2. Directory & File Structure
```text
data/raw/corrosion_segmentation/
├── Labeled images.zip            # Untouched original ZIP archive (262.97 MB)
├── dataset_manifest.json         # Machine-readable factual metadata manifest
├── INSPECTION_REPORT.md          # Comprehensive data inspection & analysis report
├── README.md                     # Dataset documentation
└── extracted/
    └── Labeled images/
        └── Labeled images/
            ├── Original images/          # 34 original high-resolution TIFF images
            ├── Label visualization/      # 36 visualization TIFFs showing marked ROIs
            └── Labels/                   # Sparse ROI coordinate patch archives
                ├── Corrosion/            # 35 .tif.zip files containing ImageJ .roi files
                └── Background/           # 35 .tif.zip files containing ImageJ .roi files
```

---

## 3. Dataset Summary & Nature of Annotations
- **Image Count:** 34 original high-resolution TIFF images (`Imag107.tif` to `Imag710.tif`).
- **Annotation Type:** **Sparse Patch-Level Pixel Annotations** (ImageJ `.roi` coordinate binary files sampling localized corrosion vs. background regions).
- **Total Annotations:** 703 sparse coordinate ROIs (352 Corrosion ROIs, 351 Background ROIs).
- **Full Dense Masks:** **Not provided.** The dataset was created for patch-based color/texture classification rather than end-to-end dense mask segmentation (e.g. YOLO-Seg).
