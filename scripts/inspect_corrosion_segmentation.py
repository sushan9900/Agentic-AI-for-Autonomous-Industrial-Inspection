import hashlib
import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

EXTRACTED_DIR = Path("data/raw/corrosion_segmentation/extracted/Labeled images")


def get_image_info(file_path: Path):
    ext = file_path.suffix.lower()
    try:
        with open(file_path, "rb") as f:
            data = f.read(65536)
            if len(data) < 24:
                return None

            if ext == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
                w, h = struct.unpack(">II", data[16:24])
                color_type = data[25]
                channels = 1 if color_type == 0 else (3 if color_type == 2 else 4)
                return {"width": w, "height": h, "channels": channels, "format": "PNG"}

            elif ext in {".jpg", ".jpeg"}:
                f.seek(0)
                full_data = f.read()
                i = 2
                while i < len(full_data) - 9:
                    if full_data[i] == 0xFF:
                        marker = full_data[i+1]
                        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                            h, w = struct.unpack(">HH", full_data[i+5:i+9])
                            channels = full_data[i+9]
                            return {"width": w, "height": h, "channels": channels, "format": "JPEG"}
                        elif marker in (0xD9, 0xDA):
                            break
                        else:
                            length = struct.unpack(">H", full_data[i+2:i+4])[0]
                            i += 2 + length
                    else:
                        i += 1
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return None


def inspect():
    print(f"--- Inspecting {EXTRACTED_DIR} ---")
    all_items = list(EXTRACTED_DIR.rglob("*"))
    files = [f for f in all_items if f.is_file()]
    dirs = [d for d in all_items if d.is_dir()]

    print(f"Total directories: {len(dirs)}")
    print(f"Total files: {len(files)}")

    print("\nDirectory breakdown:")
    for d in sorted(dirs):
        rel_d = d.relative_to(EXTRACTED_DIR)
        sub_files = [f for f in files if f.parent == d]
        print(f"  Folder: '{rel_d}' -> {len(sub_files)} files")

    ext_counts = Counter(f.suffix.lower() for f in files)
    print("\nFile extension breakdown:")
    for ext, cnt in ext_counts.most_common():
        print(f"  {ext or '[no extension]'}: {cnt}")

    # Inspect images
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    image_files = [f for f in files if f.suffix.lower() in image_exts]
    print(f"\nTotal image files: {len(image_files)}")

    # Check non-image files (CSV, TXT, JSON, MAT, etc.)
    non_images = [f for f in files if f.suffix.lower() not in image_exts]
    print(f"Total non-image/annotation files: {len(non_images)}")
    for f in non_images:
        print(f"  {f.relative_to(EXTRACTED_DIR)} ({f.stat().st_size} bytes)")
        if f.suffix.lower() in {".txt", ".csv", ".json", ".xml", ".md", ".mat"}:
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as tf:
                    print(f"    Preview:\n{tf.read(500).strip()}")
            except Exception as e:
                print(f"    Read error: {e}")

    # Separate images into raw photos vs masks/annotations
    print("\nCategorizing image files by directory/naming convention:")
    for d in dirs:
        sub_imgs = [f for f in image_files if f.parent == d]
        print(f"  Folder '{d.name}': {len(sub_imgs)} images (e.g., {[f.name for f in sub_imgs[:3]]})")

    # Image stats
    widths = []
    heights = []
    formats = Counter()
    channels = Counter()
    for img_f in image_files:
        info = get_image_info(img_f)
        if info:
            widths.append(info["width"])
            heights.append(info["height"])
            formats[info["format"]] += 1
            channels[info["channels"]] += 1

    if widths:
        print(f"\nImage resolutions: min={min(widths)}x{min(heights)}, max={max(widths)}x{max(heights)}, median={sorted(widths)[len(widths)//2]}x{sorted(heights)[len(heights)//2]}")
        print("Format breakdown:", dict(formats))
        print("Channel breakdown:", dict(channels))
        print("Common resolutions:", Counter(zip(widths, heights)).most_common(5))


if __name__ == "__main__":
    inspect()
