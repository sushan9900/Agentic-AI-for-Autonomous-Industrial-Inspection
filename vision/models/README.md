# Computer Vision Models & Model Zoo

This package contains abstract model contracts and framework-specific concrete wrappers for industrial defect inspection.

---

## Architecture & Abstraction Boundary

```text
vision/models/
├── base.py       # BaseVisionModel abstract class & exception hierarchy
├── yolo_seg.py   # YOLOSegmentationModel wrapper around Ultralytics YOLO11-Seg
└── __init__.py   # Public module exports
```

### Abstraction Rules
1. **Zero Framework Leakage:** Downstream components (orchestrators, inference pipelines, and agentic layers) interact strictly via `BaseVisionModel` and receive normalized `Detection` / `InspectionResult` Pydantic schemas.
2. **Deterministic Severity Extraction:** Measurable geometric features (mask area, bounding box area, crack length/width) are extracted in `vision.inference.severity` without hallucinating qualitative severity ratings.

---

## Available Models

### 1. YOLO11n-Seg (DeepCrack Crack Segmentation Baseline)
- **Class:** `0: crack`
- **Architecture:** `YOLO11n-seg`
- **Checkpoint:** `experiments/vision/deepcrack/baseline/weights/best.pt`
- **Test Performance:** Mask mAP@50: `0.3436`, Mask mAP@50:95: `0.1100`, Precision: `0.5151`, Recall: `0.4029`

```python
from vision.models.yolo_seg import YOLOSegmentationModel
from vision.inference.pipeline import InferencePipeline

model = YOLOSegmentationModel(
    model_path="experiments/vision/deepcrack/baseline/weights/best.pt",
    device="0",
    confidence_threshold=0.25
)
model.load()

pipeline = InferencePipeline(model=model)
result = pipeline.run_inspection(
    image_input="data/processed/deepcrack/yolo/images/test/11112.jpg",
    inspection_id="insp_101",
    component_id="PIPE-SEG-4021"
)
```
