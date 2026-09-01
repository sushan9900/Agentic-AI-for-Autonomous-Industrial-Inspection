from typing import Dict, List, Optional, Set


# Common unified taxonomy for primary industrial pipeline defect inspection
UNIFIED_TAXONOMY: Dict[int, str] = {
    0: "corrosion",
    1: "crack",
    2: "coating_damage",
    3: "surface_damage",
}

UNIFIED_TAXONOMY_INVERSE: Dict[str, int] = {
    name: idx for idx, name in UNIFIED_TAXONOMY.items()
}


class TaxonomyError(Exception):
    """Base exception for taxonomy and category mapping errors."""
    pass


class UnmappedCategoryError(TaxonomyError):
    """Raised when a source category label has no explicit mapping defined."""
    pass


class TaxonomyMapper:
    """Explicit mapper from source dataset category labels to unified inspection taxonomy."""

    def __init__(
        self,
        mapping: Optional[Dict[str, str]] = None,
        target_taxonomy: Optional[Dict[int, str]] = None,
        allow_drop_unmapped: bool = False,
    ) -> None:
        self.target_taxonomy = target_taxonomy or UNIFIED_TAXONOMY
        self.target_taxonomy_inverse = {
            name: idx for idx, name in self.target_taxonomy.items()
        }
        self.mapping = mapping or {}
        self.allow_drop_unmapped = allow_drop_unmapped

        # Validate that all targets in mapping exist in target_taxonomy
        for src, tgt in self.mapping.items():
            if tgt not in self.target_taxonomy_inverse:
                raise ValueError(
                    f"Target category '{tgt}' mapped from '{src}' is not in approved taxonomy: "
                    f"{list(self.target_taxonomy_inverse.keys())}"
                )

    def map_category_name(self, source_category: str) -> Optional[str]:
        """Maps a raw source dataset label string to the unified category string.
        
        Args:
            source_category: Raw label from source dataset.
            
        Returns:
            Unified category name, or None if dropped.
            
        Raises:
            UnmappedCategoryError: If category is unmapped and allow_drop_unmapped is False.
        """
        clean_src = source_category.strip()

        # Direct identity match if already in target taxonomy
        if clean_src in self.target_taxonomy_inverse:
            return clean_src

        if clean_src in self.mapping:
            return self.mapping[clean_src]

        if self.allow_drop_unmapped:
            return None

        raise UnmappedCategoryError(
            f"Source category '{source_category}' has no explicit mapping defined for target taxonomy "
            f"{list(self.target_taxonomy_inverse.keys())}. Define an explicit mapping in TaxonomyMapper."
        )

    def map_category_id(self, source_category: str) -> Optional[int]:
        """Maps a raw source dataset label string to the unified integer class ID."""
        unified_name = self.map_category_name(source_category)
        if unified_name is None:
            return None
        return self.target_taxonomy_inverse[unified_name]

    def get_supported_classes(self) -> List[str]:
        """Returns the list of unified class names in index order."""
        return [self.target_taxonomy[i] for i in sorted(self.target_taxonomy.keys())]


# Predefined explicit mappers for verified candidate datasets

def get_pipeline_corrosion_mapper() -> TaxonomyMapper:
    """Explicit mapper for Mendeley Pipeline Corrosion dataset (Ata et al.)."""
    return TaxonomyMapper(
        mapping={
            "uniform_corrosion": "corrosion",
            "pitting_corrosion": "corrosion",
            "corrosion": "corrosion",
            "rust": "corrosion",
            "coating_flaking": "coating_damage",
            "coating_peeling": "coating_damage",
            "paint_damage": "coating_damage",
        },
        allow_drop_unmapped=False,
    )


def get_corrosion_condition_mapper() -> TaxonomyMapper:
    """Explicit mapper for Mendeley Corrosion Condition dataset (Nash et al.)."""
    return TaxonomyMapper(
        mapping={
            "poor": "corrosion",
            "severe": "corrosion",
            "coating_breakdown": "coating_damage",
            "coating_failure": "coating_damage",
            "surface_defect": "surface_damage",
        },
        allow_drop_unmapped=True,  # Allows dropping 'fair'/healthy background annotations if needed
    )


def get_deepcrack_mapper() -> TaxonomyMapper:
    """Explicit mapper for DeepCrack dataset (Liu et al.)."""
    return TaxonomyMapper(
        mapping={
            "crack": "crack",
            "surface_crack": "crack",
            "fracture": "crack",
        },
        allow_drop_unmapped=False,
    )
