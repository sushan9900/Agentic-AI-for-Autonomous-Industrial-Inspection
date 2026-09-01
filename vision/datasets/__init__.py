"""Vision datasets management, taxonomy mapping, COCO schemas, converters, and validators."""
from vision.datasets.coco import (
    COCOAnnotation,
    COCOCategory,
    COCODataset,
    COCOImage,
)
from vision.datasets.converter import (
    COCOToYOLOConverter,
    ConversionError,
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
    TaxonomyError,
    TaxonomyMapper,
    UNIFIED_TAXONOMY,
    UNIFIED_TAXONOMY_INVERSE,
    UnmappedCategoryError,
    get_corrosion_condition_mapper,
    get_deepcrack_mapper,
    get_pipeline_corrosion_mapper,
)
from vision.datasets.validator import (
    DatasetIntegrityReport,
    DatasetValidator,
    ValidationError,
)

__all__ = [
    "COCOAnnotation",
    "COCOCategory",
    "COCODataset",
    "COCOImage",
    "COCOToYOLOConverter",
    "ConversionError",
    "CoordinateNormalizationError",
    "DatasetIntegrityReport",
    "DatasetMetadata",
    "DatasetSplitInfo",
    "DatasetSplitter",
    "DatasetTaskType",
    "DatasetValidator",
    "SourceResolution",
    "TaxonomyError",
    "TaxonomyMapper",
    "UNIFIED_TAXONOMY",
    "UNIFIED_TAXONOMY_INVERSE",
    "UnmappedCategoryError",
    "ValidationError",
    "get_corrosion_condition_mapper",
    "get_deepcrack_mapper",
    "get_pipeline_corrosion_mapper",
]
