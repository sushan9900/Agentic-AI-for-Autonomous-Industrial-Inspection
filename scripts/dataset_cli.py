import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vision.datasets.coco import COCODataset
from vision.datasets.converter import COCOToYOLOConverter
from vision.datasets.taxonomy import (
    TaxonomyMapper,
    UNIFIED_TAXONOMY,
    get_corrosion_condition_mapper,
    get_deepcrack_mapper,
    get_pipeline_corrosion_mapper,
)
from vision.datasets.validator import DatasetValidator


def inspect_dataset(dataset_path: str) -> None:
    """Inspects a dataset directory or annotation file."""
    p = Path(dataset_path)
    if not p.exists():
        print(f"Error: Dataset path '{dataset_path}' does not exist.", file=sys.stderr)
        print("Please download and place the dataset in the specified directory before inspecting.", file=sys.stderr)
        sys.exit(1)

    if p.is_dir():
        files = list(p.rglob("*"))
        image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
        images = [f for f in files if f.suffix.lower() in image_exts]
        annotations = [f for f in files if f.suffix.lower() in {".json", ".xml", ".txt"}]
        print(f"Dataset Directory Inspection: {dataset_path}")
        print(f"  Total files: {len(files)}")
        print(f"  Images detected: {len(images)}")
        print(f"  Annotation files detected: {len(annotations)}")
    elif p.is_file() and p.suffix.lower() == ".json":
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            coco = COCODataset.model_validate(data)
            print(f"COCO Annotation File Inspection: {dataset_path}")
            print(f"  Images in COCO: {len(coco.images)}")
            print(f"  Annotations: {len(coco.annotations)}")
            print(f"  Categories: {[c.name for c in coco.categories]}")
        except Exception as e:
            print(f"Error parsing COCO file '{dataset_path}': {e}", file=sys.stderr)
            sys.exit(1)


def validate_dataset(dataset_file: str, images_dir: str = None) -> None:
    """Validates dataset annotations and images."""
    p = Path(dataset_file)
    if not p.exists():
        print(f"Error: Annotation file '{dataset_file}' does not exist.", file=sys.stderr)
        print("Ensure datasets are downloaded and extracted before running validation.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        dataset = COCODataset.model_validate(data)
    except Exception as e:
        print(f"Error reading dataset JSON: {e}", file=sys.stderr)
        sys.exit(1)

    validator = DatasetValidator(
        taxonomy_mapper=TaxonomyMapper(),
        check_file_existence=bool(images_dir),
        images_base_dir=images_dir,
    )
    report = validator.validate_dataset(dataset)

    print(f"Dataset Validation Report for: {dataset_file}")
    print(f"  Images Checked: {report.total_images_checked}")
    print(f"  Annotations Checked: {report.total_annotations_checked}")
    print(f"  Class Distribution: {report.class_distribution}")
    print(f"  Status: {'PASSED' if report.is_valid else 'FAILED'}")

    if report.warnings:
        print(f"  Warnings ({len(report.warnings)}):")
        for w in report.warnings[:10]:
            print(f"    - {w}")

    if report.errors:
        print(f"  Errors ({len(report.errors)}):", file=sys.stderr)
        for err in report.errors[:10]:
            print(f"    - {err}", file=sys.stderr)
        sys.exit(1)


def convert_dataset(input_coco: str, output_dir: str, mode: str = "box") -> None:
    """Converts a COCO JSON dataset to YOLO text format."""
    in_path = Path(input_coco)
    if not in_path.exists():
        print(f"Error: Source COCO file '{input_coco}' does not exist.", file=sys.stderr)
        print("Cannot convert nonexistent dataset.", file=sys.stderr)
        sys.exit(1)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    dataset = COCODataset.model_validate(data)

    converter = COCOToYOLOConverter(taxonomy_mapper=TaxonomyMapper())
    image_map = {img.id: img for img in dataset.images}
    ann_by_image = {}
    for ann in dataset.annotations:
        ann_by_image.setdefault(ann.image_id, []).append(ann)

    converted_count = 0
    for img_id, anns in ann_by_image.items():
        img = image_map[img_id]
        label_file = out_path / f"{Path(img.file_name).stem}.txt"
        lines = []
        for ann in anns:
            if mode == "segmentation":
                line = converter.convert_annotation_to_yolo_segmentation(ann, img.width, img.height)
            else:
                line = converter.convert_annotation_to_yolo_box(ann, img.width, img.height)
            if line:
                lines.append(line)
        
        with open(label_file, "w", encoding="utf-8") as lf:
            lf.write("\n".join(lines) + "\n")
        converted_count += 1

    print(f"Successfully converted {converted_count} image annotations to YOLO {mode} format in {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Industrial Inspection Dataset Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # Inspect command
    inspect_p = subparsers.add_parser("inspect", help="Inspect dataset directory or file")
    inspect_p.add_argument("--dataset-path", required=True, help="Path to raw or processed dataset")

    # Validate command
    val_p = subparsers.add_parser("validate", help="Validate COCO annotations against taxonomy")
    val_p.add_argument("--dataset-file", required=True, help="Path to COCO JSON annotation file")
    val_p.add_argument("--images-dir", default=None, help="Optional image directory for existence checks")

    # Convert command
    conv_p = subparsers.add_parser("convert", help="Convert COCO JSON to YOLO format")
    conv_p.add_argument("--input-coco", required=True, help="Source COCO JSON file")
    conv_p.add_argument("--output-dir", required=True, help="Target YOLO labels directory")
    conv_p.add_argument("--mode", choices=["box", "segmentation"], default="box", help="Export mode")

    args = parser.parse_args()

    if args.command == "inspect":
        inspect_dataset(args.dataset_path)
    elif args.command == "validate":
        validate_dataset(args.dataset_file, args.images_dir)
    elif args.command == "convert":
        convert_dataset(args.input_coco, args.output_dir, args.mode)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
