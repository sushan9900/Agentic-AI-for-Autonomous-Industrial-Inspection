# Computer Vision Dataset Infrastructure & Production Data Pipeline

This package provides a modular, production-grade dataset engineering architecture for industrial inspection datasets. It decouples dataset ingestion and raw data formats from downstream model training and inference.

---

## 1. Core Principles
- **Raw Data Immutability:** `data/raw/` is treated as strictly read-only source of truth.
- **Reproducibility & Provenance:** Every sample is tagged with full traceability back to source archives and processing configs.
- **Group Leakage Prevention:** Structural asset IDs are preserved to guarantee disjoint partitions across `train`, `val`, and `test`.
- **Framework Independence:** All core adapters, normalization, and resizing utilities are decoupled from PyTorch/YOLO.

---

## 2. Package Architecture

```text
vision/datasets/
├── sample.py                    # Normalized DatasetSample & AnnotationType contracts
├── metadata.py                  # Typed DatasetMetadata schemas
├── taxonomy.py                  # 4-class unified industrial defect taxonomy
├── leakage.py                   # Group leakage validator & duplicate hash detector
├── splitter.py                  # Deterministic group-aware dataset partitioner
├── preprocessing.py             # Nearest-neighbor mask resizer & letterbox utilities
├── augmentation.py              # Synchronized image + mask augmentation interface
├── coco.py                      # Master COCO schema definitions
├── converter.py                 # Normalized COCO to YOLO converter
├── validator.py                 # Geometric & structural dataset validator
├── pipeline.py                  # Production dataset pipeline orchestrator
└── adapters/                    # Dataset source adapters
    ├── base.py                  # BaseDatasetAdapter interface
    ├── deepcrack.py             # DeepCrack paired RGB + binary mask adapter
    ├── corrosion_detection.py   # High-resolution unannotated corrosion adapter
    └── corrosion_segmentation.py# ImageJ sparse coordinate .roi patch adapter
```

---

## 3. Dataset Sample Contract

Every sample across all industrial datasets is normalized into a `DatasetSample` instance:

```python
class DatasetSample(BaseModel):
    dataset_id: str
    sample_id: str
    image_path: Path
    annotation_path: Optional[Path]
    annotation_type: AnnotationType
    source_split: Optional[str]
    group_id: str
    original_labels: List[str]
    image_width: int
    image_height: int
    channels: int
    metadata: Dict[str, Any]
    provenance: ProvenanceRecord
```

---

## 4. Group Leakage Prevention & Splitting Strategy

### DeepCrack Asset Grouping
DeepCrack filename stems such as `11289-1` through `11289-10` originate from the same physical structure. The adapter extracts the parent group `11289` as `group_id`.

The `DatasetSplitter` assigns entire groups atomically to a single split partition, ensuring:
$$\text{train\_groups} \cap \text{val\_groups} = \emptyset$$
$$\text{train\_groups} \cap \text{test\_groups} = \emptyset$$
$$\text{val\_groups} \cap \text{test\_groups} = \emptyset$$

---

## 5. Nearest-Neighbor Mask Preservation

When resizing segmentation masks, bilinear or bicubic interpolation creates intermediate floating-point values along boundaries. This package enforces **strict nearest-neighbor interpolation** (`nearest_neighbor_resize_2d` and `letterbox_mask_2d`), ensuring binary crack masks remain strictly discrete with values in $\{0, 255\}$.

---

## 6. Running the Production Pipeline

To execute the dataset preparation pipeline and generate processed manifests:

```powershell
.venv\Scripts\python.exe -m vision.datasets.pipeline
```

Processed artifacts and manifests are saved to:
- `data/processed/deepcrack/manifest.json`
- `data/processed/corrosion_detection/manifest.json`
- `data/processed/corrosion_segmentation/manifest.json`
- `data/processed/dataset_pipeline_manifest.json`
