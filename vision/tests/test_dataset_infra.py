import pytest
from pydantic import ValidationError

from vision.datasets.coco import (
    COCOAnnotation,
    COCOCategory,
    COCODataset,
    COCOImage,
)
from vision.datasets.converter import (
    COCOToYOLOConverter,
    CoordinateNormalizationError,
)
from vision.datasets.metadata import (
    DatasetMetadata,
    DatasetSplitInfo,
    DatasetTaskType,
    SourceResolution,
)
from vision.datasets.splitter import DatasetSplitter
from vision.datasets.taxonomy import (
    TaxonomyMapper,
    UNIFIED_TAXONOMY,
    UnmappedCategoryError,
    get_corrosion_condition_mapper,
    get_deepcrack_mapper,
    get_pipeline_corrosion_mapper,
)
from vision.datasets.validator import DatasetValidator


def test_dataset_metadata_validation():
    """Test valid dataset metadata creation."""
    meta = DatasetMetadata(
        dataset_name="mendeley_pipeline_corrosion",
        source="Ata et al., 2021",
        version="1.0.0",
        license="CC BY 4.0",
        annotation_format="YOLO/VOC",
        image_count=1480,
        categories=["uniform_corrosion", "pitting_corrosion", "coating_flaking"],
        splits=DatasetSplitInfo(train_count=1036, val_count=222, test_count=222, total_count=1480),
        resolution_info=SourceResolution(typical_resolution="1920x1080"),
        intended_task=DatasetTaskType.OBJECT_DETECTION,
    )
    assert meta.dataset_name == "mendeley_pipeline_corrosion"
    assert meta.image_count == 1480
    assert meta.splits.train_count == 1036


def test_taxonomy_mapping_valid():
    """Test explicit mapping from source labels to unified taxonomy."""
    mapper = get_pipeline_corrosion_mapper()

    assert mapper.map_category_name("uniform_corrosion") == "corrosion"
    assert mapper.map_category_id("uniform_corrosion") == 0

    assert mapper.map_category_name("coating_flaking") == "coating_damage"
    assert mapper.map_category_id("coating_flaking") == 2


def test_taxonomy_mapping_unmapped_rejection():
    """Test that unmapped source labels raise UnmappedCategoryError when dropping is disabled."""
    mapper = get_pipeline_corrosion_mapper()

    with pytest.raises(UnmappedCategoryError):
        mapper.map_category_name("unknown_foreign_defect")


def test_coco_models_and_bbox_validation():
    """Test COCO schema validation with valid and invalid bounding boxes."""
    img = COCOImage(id=1, file_name="pipe_001.jpg", width=1920, height=1080)
    assert img.width == 1920

    # Valid annotation
    ann = COCOAnnotation(
        id=101,
        image_id=1,
        category_id=0,
        bbox=[100.0, 150.0, 300.0, 200.0],
        area=60000.0,
        segmentation=[[100.0, 150.0, 400.0, 150.0, 400.0, 350.0, 100.0, 350.0]]
    )
    assert ann.bbox == [100.0, 150.0, 300.0, 200.0]

    # Invalid negative width
    with pytest.raises(ValidationError):
        COCOAnnotation(
            id=102,
            image_id=1,
            category_id=0,
            bbox=[100.0, 150.0, -50.0, 200.0],
            area=0.0
        )


def test_coco_to_yolo_coordinate_normalization():
    """Test accurate bounding box conversion from COCO pixel coords to YOLO [0, 1] relative coords."""
    converter = COCOToYOLOConverter()
    
    # Image 1000x1000, Box: x=100, y=200, w=400, h=600 -> Center: x=300, y=500 -> Norm: (0.3, 0.5, 0.4, 0.6)
    norm_x, norm_y, norm_w, norm_h = converter.normalize_bbox(
        bbox=[100.0, 200.0, 400.0, 600.0],
        img_width=1000,
        img_height=1000
    )
    assert pytest.approx(norm_x) == 0.3
    assert pytest.approx(norm_y) == 0.5
    assert pytest.approx(norm_w) == 0.4
    assert pytest.approx(norm_h) == 0.6

    # Test line formatting
    ann = COCOAnnotation(
        id=1,
        image_id=1,
        category_id=0,
        bbox=[100.0, 200.0, 400.0, 600.0],
        area=240000.0
    )
    line = converter.convert_annotation_to_yolo_box(ann, img_width=1000, img_height=1000)
    assert line == "0 0.300000 0.500000 0.400000 0.600000"


def test_polygon_normalization():
    """Test polygon vertex normalization."""
    converter = COCOToYOLOConverter()
    poly = [0.0, 0.0, 500.0, 0.0, 500.0, 1000.0, 0.0, 1000.0]
    norm_poly = converter.normalize_polygon(poly, img_width=1000, img_height=1000)
    assert norm_poly == [0.0, 0.0, 0.5, 0.0, 0.5, 1.0, 0.0, 1.0]


def test_dataset_validator():
    """Test dataset integrity checks and error detection."""
    validator = DatasetValidator(taxonomy_mapper=TaxonomyMapper())

    # Build dataset with 1 valid image & annotation, 1 orphaned annotation
    dataset = COCODataset(
        images=[
            COCOImage(id=1, file_name="pipe_01.jpg", width=640, height=480),
        ],
        annotations=[
            COCOAnnotation(
                id=1,
                image_id=1,
                category_id=0,
                bbox=[10.0, 10.0, 50.0, 50.0],
                area=2500.0
            ),
            COCOAnnotation(
                id=2,
                image_id=999,  # Nonexistent image ID
                category_id=1,
                bbox=[20.0, 20.0, 40.0, 40.0],
                area=1600.0
            )
        ],
        categories=[
            COCOCategory(id=0, name="corrosion"),
            COCOCategory(id=1, name="crack"),
        ]
    )

    report = validator.validate_dataset(dataset)
    assert report.total_images_checked == 1
    assert report.total_annotations_checked == 2
    assert report.is_valid is False
    assert any("missing image ID 999" in err for err in report.errors)


def test_dataset_splitter_and_leakage_detection():
    """Test group-based splitting and split leakage checking."""
    dataset = COCODataset(
        images=[
            COCOImage(id=1, file_name="pipeA_1.jpg", width=640, height=480, asset_id="pipe_A"),
            COCOImage(id=2, file_name="pipeA_2.jpg", width=640, height=480, asset_id="pipe_A"),
            COCOImage(id=3, file_name="pipeB_1.jpg", width=640, height=480, asset_id="pipe_B"),
            COCOImage(id=4, file_name="pipeC_1.jpg", width=640, height=480, asset_id="pipe_C"),
        ],
        annotations=[
            COCOAnnotation(id=1, image_id=1, category_id=0, bbox=[10.0, 10.0, 20.0, 20.0], area=400.0),
            COCOAnnotation(id=2, image_id=2, category_id=0, bbox=[10.0, 10.0, 20.0, 20.0], area=400.0),
            COCOAnnotation(id=3, image_id=3, category_id=1, bbox=[10.0, 10.0, 20.0, 20.0], area=400.0),
            COCOAnnotation(id=4, image_id=4, category_id=2, bbox=[10.0, 10.0, 20.0, 20.0], area=400.0),
        ],
        categories=[
            COCOCategory(id=0, name="corrosion"),
            COCOCategory(id=1, name="crack"),
            COCOCategory(id=2, name="coating_damage"),
        ]
    )

    splitter = DatasetSplitter(seed=42)
    train, val, test = splitter.split_by_group(dataset, group_key="asset_id", train_ratio=0.5, val_ratio=0.25, test_ratio=0.25)

    # Check for leakage
    leakages = DatasetValidator.check_split_leakage(train.images, val.images, test.images)
    assert len(leakages) == 0

    # Ensure pipe_A frames are together in the same split
    train_asset_ids = {img.asset_id for img in train.images}
    test_asset_ids = {img.asset_id for img in test.images}
    assert train_asset_ids.isdisjoint(test_asset_ids)
