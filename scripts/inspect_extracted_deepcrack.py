import hashlib
import json
import os
import shutil
import struct
import sys
import zipfile
from collections import Counter
from pathlib import Path

DATASET_DIR = Path("data/raw/deepcrack")
ARCHIVE_PATH = DATASET_DIR / "DeepCrack.zip"
REPO_ZIP = DATASET_DIR / "repo/dataset/DeepCrack.zip"
EXTRACTED_DIR = DATASET_DIR / "extracted"


def handle_remove_readonly(func, path, exc):
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)


def prepare_archive():
    if not ARCHIVE_PATH.exists() and REPO_ZIP.exists():
        print(f"Moving {REPO_ZIP} to {ARCHIVE_PATH}...")
        shutil.copy2(REPO_ZIP, ARCHIVE_PATH)
    
    # Remove temporary clone repo folder
    repo_dir = DATASET_DIR / "repo"
    if repo_dir.exists():
        shutil.rmtree(repo_dir, onerror=handle_remove_readonly)


def verify_archive() -> bool:
    print(f"Verifying archive: {ARCHIVE_PATH}")
    if not ARCHIVE_PATH.exists():
        print(f"Error: Archive {ARCHIVE_PATH} does not exist.", file=sys.stderr)
        return False

    size = ARCHIVE_PATH.stat().st_size
    print(f"  Archive Size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")

    print("  Calculating full SHA-256...")
    h = hashlib.sha256()
    with open(ARCHIVE_PATH, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    calc_hash = h.hexdigest()
    print(f"  SHA-256: {calc_hash}")

    print("  Testing ZIP integrity...")
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as z:
        bad_file = z.testzip()
        if bad_file:
            print(f"  ZIP test failed on {bad_file}!", file=sys.stderr)
            return False
        n_entries = len(z.infolist())
        print(f"  [OK] ZIP integrity check passed ({n_entries} entries in archive).")
    return True


def safe_extract():
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {ARCHIVE_PATH.name} to {EXTRACTED_DIR}...")
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as z:
        for member in z.infolist():
            target_path = (EXTRACTED_DIR / member.filename).resolve()
            try:
                target_path.relative_to(EXTRACTED_DIR.resolve())
            except ValueError:
                print(f"SECURITY ALERT: Unsafe member path: {member.filename}", file=sys.stderr)
                sys.exit(1)
        z.extractall(EXTRACTED_DIR)
    print("  [OK] Extraction complete.")


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
                channels = 1 if color_type in (0, 3) else (3 if color_type == 2 else 4)
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


def inspect_deepcrack():
    print(f"\n--- Scanning DeepCrack Extracted Files in {EXTRACTED_DIR} ---")
    all_files = list(EXTRACTED_DIR.rglob("*"))
    files = [f for f in all_files if f.is_file()]
    dirs = [d for d in all_files if d.is_dir()]

    print(f"Total directories: {len(dirs)}")
    print(f"Total files: {len(files)}")

    print("\nDirectory breakdown:")
    for d in sorted(dirs):
        sub_files = [f for f in files if f.parent == d]
        print(f"  {d.relative_to(EXTRACTED_DIR)}: {len(sub_files)} files")

    # Group by split folders: train_img, train_lab, test_img, test_lab
    train_img_files = sorted((EXTRACTED_DIR / "train_img").glob("*.jpg"))
    train_lab_files = sorted((EXTRACTED_DIR / "train_lab").glob("*.png"))
    test_img_files = sorted((EXTRACTED_DIR / "test_img").glob("*.jpg"))
    test_lab_files = sorted((EXTRACTED_DIR / "test_lab").glob("*.png"))

    print("\nSplit Counts:")
    print(f"  Train RGB images (train_img): {len(train_img_files)}")
    print(f"  Train masks (train_lab):      {len(train_lab_files)}")
    print(f"  Test RGB images (test_img):   {len(test_img_files)}")
    print(f"  Test masks (test_lab):        {len(test_lab_files)}")
    print(f"  Total RGB images:             {len(train_img_files) + len(test_img_files)}")
    print(f"  Total Ground Truth Masks:     {len(train_lab_files) + len(test_lab_files)}")

    # 1. Pairing verification
    print("\nVerifying Image-Mask Pairing:")
    train_img_stems = {f.stem for f in train_img_files}
    train_lab_stems = {f.stem for f in train_lab_files}
    train_missing_labs = train_img_stems - train_lab_stems
    train_orphan_labs = train_lab_stems - train_img_stems
    print(f"  Train set pairing: {len(train_img_files)} images <-> {len(train_lab_files)} masks")
    print(f"  Train missing masks: {len(train_missing_labs)}, Train orphan masks: {len(train_orphan_labs)}")

    test_img_stems = {f.stem for f in test_img_files}
    test_lab_stems = {f.stem for f in test_lab_files}
    test_missing_labs = test_img_stems - test_lab_stems
    test_orphan_labs = test_lab_stems - test_img_stems
    print(f"  Test set pairing: {len(test_img_files)} images <-> {len(test_lab_files)} masks")
    print(f"  Test missing masks: {len(test_missing_labs)}, Test orphan masks: {len(test_orphan_labs)}")

    # 2. Split leakage check
    print("\nChecking Split Leakage:")
    leakage = train_img_stems.intersection(test_img_stems)
    print(f"  Train-Test filename overlap: {len(leakage)} images")

    # 3. Image Dimension & Channel Analysis
    all_rgb = train_img_files + test_img_files
    all_masks = train_lab_files + test_lab_files

    rgb_widths, rgb_heights, rgb_channels = [], [], Counter()
    for f in all_rgb:
        info = get_image_info(f)
        if info:
            rgb_widths.append(info["width"])
            rgb_heights.append(info["height"])
            rgb_channels[info["channels"]] += 1

    mask_widths, mask_heights, mask_channels = [], [], Counter()
    for f in all_masks:
        info = get_image_info(f)
        if info:
            mask_widths.append(info["width"])
            mask_heights.append(info["height"])
            mask_channels[info["channels"]] += 1

    print("\nRGB Images Resolution Statistics:")
    print(f"  Widths: min={min(rgb_widths)}, max={max(rgb_widths)}, median={sorted(rgb_widths)[len(rgb_widths)//2]}")
    print(f"  Heights: min={min(rgb_heights)}, max={max(rgb_heights)}, median={sorted(rgb_heights)[len(rgb_heights)//2]}")
    print(f"  Common resolutions: {Counter(zip(rgb_widths, rgb_heights)).most_common()}")
    print(f"  Channels: {dict(rgb_channels)}")

    print("\nMasks Resolution Statistics:")
    print(f"  Widths: min={min(mask_widths)}, max={max(mask_widths)}, median={sorted(mask_widths)[len(mask_widths)//2]}")
    print(f"  Heights: min={min(mask_heights)}, max={max(mask_heights)}, median={sorted(mask_heights)[len(mask_heights)//2]}")
    print(f"  Common resolutions: {Counter(zip(mask_widths, mask_heights)).most_common()}")
    print(f"  Channels: {dict(mask_channels)}")

    # 4. Duplicate Check
    hashes = {}
    duplicates = []
    for f in all_rgb:
        with open(f, "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()
        if h in hashes:
            duplicates.append((f.name, hashes[h]))
        else:
            hashes[h] = f.name
    print(f"\nDuplicate RGB images across dataset: {len(duplicates)}")


if __name__ == "__main__":
    prepare_archive()
    if verify_archive():
        safe_extract()
        inspect_deepcrack()
