import hashlib
import json
import os
import struct
import sys
import zipfile
from collections import Counter
from pathlib import Path

DATASET_DIR = Path("data/raw/corrosion_detection")
ARCHIVE_PATH = DATASET_DIR / "Corrosion_Data.zip"
EXTRACTED_DIR = DATASET_DIR / "extracted"
EXPECTED_SHA256 = "f667aedcb6be8e25bdd3a454d106f9304953ad4eb5f267f6798b228be397c07a"
EXPECTED_TOTAL_SIZE = 662667730


def verify_archive() -> bool:
    print(f"Verifying archive: {ARCHIVE_PATH}")
    if not ARCHIVE_PATH.exists():
        print(f"Error: Archive {ARCHIVE_PATH} does not exist.", file=sys.stderr)
        return False

    size = ARCHIVE_PATH.stat().st_size
    print(f"  Archive Size: {size:,} bytes")
    if size != EXPECTED_TOTAL_SIZE:
        print(f"Error: Expected {EXPECTED_TOTAL_SIZE:,} bytes, found {size:,} bytes.", file=sys.stderr)
        return False

    print("  Computing SHA-256...")
    h = hashlib.sha256()
    with open(ARCHIVE_PATH, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    calc_hash = h.hexdigest()
    print(f"  SHA-256: {calc_hash}")
    if calc_hash != EXPECTED_SHA256:
        print("Error: SHA-256 mismatch.", file=sys.stderr)
        return False

    print("  Testing ZIP integrity...")
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as z:
        if z.testzip() is not None:
            print("Error: ZIP file test failed.", file=sys.stderr)
            return False
    print("  [OK] Archive verified successfully.")
    return True


def safe_extract():
    print(f"Extracting safely into {EXTRACTED_DIR}...")
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as z:
        for member in z.infolist():
            # Check for path traversal attacks
            target_path = EXTRACTED_DIR.resolve() / member.filename
            try:
                target_path.resolve().relative_to(EXTRACTED_DIR.resolve())
            except ValueError:
                print(f"SECURITY ALERT: Unsafe archive member path: {member.filename}", file=sys.stderr)
                sys.exit(1)
        
        z.extractall(EXTRACTED_DIR)
    print("  [OK] Extraction complete.")


def get_image_info(file_path: Path):
    """Parses image resolution and channels from JPEG/PNG headers in pure Python."""
    ext = file_path.suffix.lower()
    try:
        with open(file_path, "rb") as f:
            data = f.read(65536)
            if len(data) < 24:
                return None

            # PNG
            if ext == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
                w, h = struct.unpack(">II", data[16:24])
                color_type = data[25]
                channels = 1 if color_type == 0 else (3 if color_type == 2 else 4)
                return {"width": w, "height": h, "channels": channels, "format": "PNG"}

            # JPEG
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
                        elif marker == 0xD9 or marker == 0xDA:
                            break
                        else:
                            length = struct.unpack(">H", full_data[i+2:i+4])[0]
                            i += 2 + length
                    else:
                        i += 1
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return None


def inspect_dataset():
    print(f"\n--- Scanning Extracted Files in {EXTRACTED_DIR} ---")
    all_files = list(EXTRACTED_DIR.rglob("*"))
    files = [f for f in all_files if f.is_file()]
    dirs = [d for d in all_files if d.is_dir()]
    
    print(f"Total directories: {len(dirs)}")
    print(f"Total files: {len(files)}")
    
    ext_counter = Counter(f.suffix.lower() for f in files)
    print("File extension breakdown:")
    for ext, count in ext_counter.most_common():
        print(f"  {ext or '[no extension]'}: {count}")

    # Inspect directory tree
    print("\nDirectory structure:")
    for d in sorted(dirs):
        rel_d = d.relative_to(EXTRACTED_DIR)
        n_subfiles = len([f for f in files if f.parent == d])
        print(f"  - {rel_d} ({n_subfiles} files)")

    # Image analysis
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    image_files = [f for f in files if f.suffix.lower() in image_exts]
    print(f"\nTotal image files: {len(image_files)}")

    image_details = []
    corrupted_images = []
    file_hashes = {}
    duplicate_files = []

    widths = []
    heights = []
    aspect_ratios = []
    channels_counter = Counter()

    for img_p in image_files:
        # Check hash
        with open(img_p, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        if h in file_hashes:
            duplicate_files.append((str(img_p.relative_to(EXTRACTED_DIR)), file_hashes[h]))
        else:
            file_hashes[h] = str(img_p.relative_to(EXTRACTED_DIR))

        info = get_image_info(img_p)
        if info is None:
            corrupted_images.append(str(img_p.relative_to(EXTRACTED_DIR)))
        else:
            widths.append(info["width"])
            heights.append(info["height"])
            aspect_ratios.append(round(info["width"] / info["height"], 3))
            channels_counter[info["channels"]] += 1
            image_details.append({
                "file": str(img_p.relative_to(EXTRACTED_DIR)),
                "name": img_p.name,
                "width": info["width"],
                "height": info["height"],
                "channels": info["channels"],
                "format": info["format"],
                "size_bytes": img_p.stat().st_size
            })

    print(f"Readable images: {len(image_details)}")
    print(f"Corrupted images: {len(corrupted_images)}")
    print(f"Duplicate image contents: {len(duplicate_files)}")

    if widths:
        print(f"Widths: min={min(widths)}, max={max(widths)}, median={sorted(widths)[len(widths)//2]}")
        print(f"Heights: min={min(heights)}, max={max(heights)}, median={sorted(heights)[len(heights)//2]}")
        common_res = Counter(zip(widths, heights)).most_common(5)
        print("Most common resolutions:")
        for (w, h), cnt in common_res:
            print(f"  {w}x{h}: {cnt} images ({cnt/len(widths)*100:.1f}%)")
        print("Channel distribution:")
        for ch, cnt in channels_counter.items():
            print(f"  {ch} channels ({'RGB' if ch==3 else ('Grayscale' if ch==1 else 'RGBA')}): {cnt}")

    # Annotation analysis
    non_image_files = [f for f in files if f.suffix.lower() not in image_exts]
    print(f"\nNon-image files ({len(non_image_files)}):")
    for f in non_image_files:
        print(f"  {f.relative_to(EXTRACTED_DIR)} ({f.stat().st_size} bytes)")
        if f.suffix.lower() in {".txt", ".json", ".xml", ".csv", ".mat", ".md"}:
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as tf:
                    sample_content = tf.read(500)
                print(f"    Preview: {sample_content.strip()[:200]}")
            except Exception as e:
                print(f"    Could not preview: {e}")

    # Inspect subfolder naming as potential category structure
    folder_categories = Counter(f.parent.name for f in image_files)
    print("\nImage distribution across directories:")
    for fol, cnt in folder_categories.items():
        print(f"  Folder '{fol}': {cnt} images")

    return {
        "files_count": len(files),
        "dirs_count": len(dirs),
        "image_count": len(image_files),
        "readable_images": len(image_details),
        "corrupted_images": len(corrupted_images),
        "duplicates_count": len(duplicate_files),
        "duplicates": duplicate_files,
        "widths": {"min": min(widths), "max": max(widths), "median": sorted(widths)[len(widths)//2]} if widths else {},
        "heights": {"min": min(heights), "max": max(heights), "median": sorted(heights)[len(heights)//2]} if heights else {},
        "common_resolutions": [f"{w}x{h} ({cnt})" for (w, h), cnt in Counter(zip(widths, heights)).most_common(5)] if widths else [],
        "channels": dict(channels_counter),
        "folder_breakdown": dict(folder_categories),
        "non_image_files": [str(f.relative_to(EXTRACTED_DIR)) for f in non_image_files],
        "image_details_sample": image_details[:5]
    }


if __name__ == "__main__":
    if verify_archive():
        safe_extract()
        results = inspect_dataset()
        print("\nInspection complete.")
