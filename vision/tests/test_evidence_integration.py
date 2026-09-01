"""Integration test for VisionEvidence generation with trained YOLO11-Seg checkpoint and real test image."""

from pathlib import Path
import pytest
from vision.inference.pipeline import InferencePipeline
from vision.models.yolo_seg import YOLOSegmentationModel
from vision.schemas.evidence import InspectionStatus, VisionEvidence

MODEL_PATH = Path("experiments/vision/deepcrack/baseline/weights/best.pt")
TEST_IMAGE = Path("data/processed/deepcrack/yolo/images/test/11112.jpg")


@pytest.mark.integration
def test_real_model_evidence_generation_and_json_roundtrip(tmp_path: Path):
    if not MODEL_PATH.exists() or not TEST_IMAGE.exists():
        pytest.skip("Model weights or test image not available for integration test.")

    model = YOLOSegmentationModel(model_path=MODEL_PATH, device="0" if pytest.importorskip("torch").cuda.is_available() else "cpu", confidence_threshold=0.25)
    model.load()

    pipeline = InferencePipeline(model=model)
    evidence = pipeline.run_inspection_evidence(
        image_path=str(TEST_IMAGE),
        component_id="PIPE-TEST-INTEG-001"
    )

    # 1. Assert schema contracts
    assert isinstance(evidence, VisionEvidence)
    assert evidence.schema_version == "1.0"
    assert evidence.component_id == "PIPE-TEST-INTEG-001"
    assert evidence.source_image.filename == TEST_IMAGE.name
    assert len(evidence.source_image.sha256_hash) == 64
    assert len(evidence.model.checkpoint_sha256) == 64
    assert evidence.processing.inference_ms > 0.0

    # 2. Test JSON file serialization
    out_json = tmp_path / "evidence_output.json"
    out_json.write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
    assert out_json.exists()

    # 3. Test JSON re-parsing and validation
    loaded_evidence = VisionEvidence.model_validate_json(out_json.read_text(encoding="utf-8"))
    assert loaded_evidence.inspection_id == evidence.inspection_id
    assert loaded_evidence.status == evidence.status
    assert len(loaded_evidence.detections) == len(evidence.detections)
