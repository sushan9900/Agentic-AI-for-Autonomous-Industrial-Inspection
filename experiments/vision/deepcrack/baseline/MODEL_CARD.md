# Model Card: YOLO11n-Seg DeepCrack Crack Segmentation Baseline

## Model Details
- **Model Name:** `yolo11n-seg_deepcrack_baseline`
- **Architecture:** YOLO11 Nano Segmentation (`YOLO11n-seg`)
- **Framework:** Ultralytics (v8.4.136) / PyTorch (v2.6.0+cu124)
- **Parameters:** 2,834,763 (fused)
- **GFLOPs:** 9.6 GFLOPs
- **Primary Task:** Binary Instance & Semantic Crack Segmentation
- **Class Taxonomy:** Single-class `0: crack`

---

## Training Dataset & Provenance
- **Dataset:** DeepCrack (Liu et al., 2019)
- **Source Archive:** `DeepCrack.zip` (SHA256: `ec3fc2bee3b71c2cc3c74739cbc51c97b77f78193d08ce3dda0e16d7d41bf585`)
- **Split Configuration:** Group-aware deterministic split (Seed: 42, Ratios: 70% Train, 15% Val, 15% Test)
  - Train: 378 images (1,248 crack polygon instances)
  - Val: 73 images (317 crack polygon instances)
  - Test: 86 images (340 crack polygon instances)
- **Leakage Invariants:** Verified disjoint group IDs ($\text{Train} \cap \text{Val} \cap \text{Test} = \emptyset$)

---

## Training Configuration & Hardware
- **Epochs:** 50
- **Image Size:** 640 x 640
- **Batch Size:** 8
- **Optimizer:** AdamW (auto-selected)
- **Base Learning Rate ($lr_0$):** 0.01
- **Hardware:** NVIDIA GeForce RTX 3050 Laptop GPU (4096 MiB VRAM)
- **Training Duration:** 1154.5 seconds (~19.24 minutes)

---

## Evaluation Metrics

### Validation Split (73 images)
| Metric | Mask Segmentation | Bounding Box |
| :--- | :--- | :--- |
| **Precision** | 0.4631 | 0.3630 |
| **Recall** | 0.3060 | 0.3660 |
| **mAP@50** | **0.3034** | 0.3040 |
| **mAP@50:95** | **0.0892** | 0.1460 |

### Held-Out Test Split (86 images — Evaluated Once)
| Metric | Mask Segmentation | Bounding Box |
| :--- | :--- | :--- |
| **Precision** | 0.5151 | 0.5210 |
| **Recall** | 0.4029 | 0.4650 |
| **mAP@50** | **0.3436** | 0.3990 |
| **mAP@50:95** | **0.1100** | 0.2110 |

---

## Measurable Severity Features
The model feeds predictions into `vision.inference.severity.extract_severity_features` to compute:
- `affected_area_percentage`: Percentage of image area enclosed by predicted crack mask polygon.
- `bounding_box_area_percentage`: Percentage of total surface area covered by bounding box.
- `crack_length_pixels`: Approximate length calculated via bounding diagonal.
- `crack_width_estimate`: Estimated average crack width in pixels.

---

## Known Limitations & Generalization Warnings
> [!WARNING]
> - **Crack-Only Baseline:** This model is trained strictly on crack patterns. It **does NOT detect corrosion, coating loss, or geometric deformations**.
> - **Domain Gap:** DeepCrack consists primarily of concrete pavement and masonry cracks. Performance on reflective steel pipes, welds, and underwater hulls will require domain adaptation.
> - **Baseline Resolution:** High-aspect-ratio hairline cracks narrower than 2 pixels may suffer from spatial downsampling at 640x640 resolution.
