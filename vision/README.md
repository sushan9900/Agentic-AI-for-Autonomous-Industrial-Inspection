# Computer Vision Subsystem

The Computer Vision subsystem serves as the perception layer of the **Agentic AI for Autonomous Industrial Inspection** platform. It processes visual inspection feeds (images/video), detects physical surface defects, extracts geometric and visual severity features, and outputs normalized structured inspection contracts.

> [!IMPORTANT]
> **Current Status (Phase 1F):**
> - **Production CV Data Pipeline:** Group-aware deterministic splitting (zero leakage), nearest-neighbor discrete mask preservation, and unified metadata manifests.
> - **Trained Baseline Model:** `YOLO11n-seg` trained on DeepCrack (50 epochs on NVIDIA RTX 3050 GPU), delivering Mask mAP@50 = `0.3436` and Box mAP@50 = `0.3990` on held-out test split.
> - **Inference Engine:** Fully integrated with `BaseVisionModel` and `InferencePipeline`, generating structured `InspectionResult` Pydantic contracts.

---

## 1. Subsystem Architecture & Separation of Concerns

The CV subsystem is strictly decoupled from the Agentic AI decision layer:

```text
Visual Input (Image/Video)
           ↓
  ImagePreprocessor (Validation & Normalization)
           ↓
  YOLOSegmentationModel (Forward Inference)
           ↓
  SeverityFeatureExtractor (Measurable Geometric & Spatial Properties)
           ↓
  InspectionResult (Standardized Pydantic Data Contract)
           ↓
  [Sent to Agentic AI Reasoning Layer]
```

- **Perception vs Reasoning**: The CV layer is solely responsible for perception (identifying *what* defect is present, *where* it is located, and its *measurable visual attributes*).
- **Subsystem Decoupling**: The downstream Agentic layer consumes only structured `InspectionResult` payloads. The CV model can be swapped (e.g. YOLO, SegFormer, PatchCore) without modifying the agent reasoning engine.

---

## 2. Model Zoo & Inference (`BaseVisionModel`)

Defined in [`vision.models.base.BaseVisionModel`](file:///c:/sushan_repos/Agentic-AI-for-Autonomous-Industrial-Inspection/vision/models/base.py) and implemented by [`YOLOSegmentationModel`](file:///c:/sushan_repos/Agentic-AI-for-Autonomous-Industrial-Inspection/vision/models/yolo_seg.py):

* `load()`: Loads weights (`best.pt`) onto target compute device (`cpu`, `cuda:0`).
* `predict()`: Runs forward pass, parses segmentation masks, and computes measurable severity features.
* `metadata()`: Returns model identification, architecture, and version specifications.

---

## 3. Measurable Severity Features (`SeverityFeatures`)

Extracts deterministic properties without subjective hallucinations:
- `affected_area_percentage`: Pixel/polygon surface coverage percentage.
- `bounding_box_area_percentage`: Percentage of image area occupied by bounding box.
- `crack_length_pixels`: Approximate length calculated via bounding diagonal.
- `crack_width_estimate`: Estimated average crack width in pixels.

---

## 4. CLI Inference Tool

Run inference on any inspection image:

```powershell
.venv\Scripts\python.exe scripts/run_vision_inference.py `
    --image data/processed/deepcrack/yolo/images/test/11112.jpg `
    --model experiments/vision/deepcrack/baseline/weights/best.pt `
    --device 0 `
    --save-overlay
```
