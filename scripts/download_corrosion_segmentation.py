import argparse
import hashlib
import os
import sys
import time
import zipfile
from pathlib import Path
import httpx

DATASET_DIR = Path("data/raw/corrosion_segmentation")

FILES_META = {
    "labeled_images": {
        "filename": "Labeled images.zip",
        "archive_path": DATASET_DIR / "Labeled images.zip",
        "url": "https://data.mendeley.com/public-files/datasets/kcyn4nhv2c/files/ee33e15a-c7ba-46f8-a06d-619c69d0f950/file_downloaded",
        "expected_size": 262967506,
        "expected_sha256": "6fbd29524a81f4d8250a3cf978da09ad09d48f65522677792156d0bdf454fcce"
    },
    "complete_database": {
        "filename": "Complete database.zip",
        "archive_path": DATASET_DIR / "Complete database.zip",
        "url": "https://data.mendeley.com/public-files/datasets/kcyn4nhv2c/files/32c38761-2171-41d8-8319-f5701fbfa731/file_downloaded",
        "expected_size": 2211263435,
        "expected_sha256": "d7711eb1d453559d3c9c26f3641c09675edd86aabfd58b9704a5693cc87d548d"
    }
}


def verify_archive(archive_path: Path, expected_size: int, expected_sha256: str) -> bool:
    if not archive_path.exists():
        return False
    size = archive_path.stat().st_size
    print(f"\nVerifying {archive_path.name}...")
    print(f"  Size on disk: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
    if size != expected_size:
        print(f"  Size mismatch: expected {expected_size:,} bytes.", file=sys.stderr)
        return False

    print("  Calculating full SHA-256...")
    h = hashlib.sha256()
    with open(archive_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    calc_hash = h.hexdigest()
    print(f"  Calculated SHA-256: {calc_hash}")
    print(f"  Expected SHA-256:   {expected_sha256}")
    if calc_hash != expected_sha256:
        print("  SHA-256 mismatch!", file=sys.stderr)
        return False
    print("  [OK] SHA-256 verified successfully.")

    print("  Testing ZIP integrity...")
    try:
        with zipfile.ZipFile(archive_path, "r") as z:
            if z.testzip() is not None:
                print("  ZIP test failed!", file=sys.stderr)
                return False
            print(f"  [OK] ZIP integrity check passed ({len(z.infolist())} entries).")
            return True
    except Exception as e:
        print(f"  ZIP open error: {e}", file=sys.stderr)
        return False


def download_file(file_key: str) -> bool:
    meta = FILES_META[file_key]
    archive_path = meta["archive_path"]
    expected_size = meta["expected_size"]
    expected_sha256 = meta["expected_sha256"]
    url = meta["url"]

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    if archive_path.exists() and archive_path.stat().st_size == expected_size:
        print(f"{meta['filename']} already downloaded. Verifying...")
        return verify_archive(archive_path, expected_size, expected_sha256)

    existing_bytes = 0
    if archive_path.exists():
        existing_bytes = archive_path.stat().st_size
        print(f"Found existing partial file for {meta['filename']}: {existing_bytes:,} bytes")

    if existing_bytes > expected_size:
        print(f"Error: Existing file size exceeds expected size. Aborting.", file=sys.stderr)
        return False

    headers = {"User-Agent": "Mozilla/5.0"}
    is_resuming = existing_bytes > 0
    open_mode = "ab" if is_resuming else "wb"

    if is_resuming:
        headers["Range"] = f"bytes={existing_bytes}-"
        print(f"Initiating resume request: Range: bytes={existing_bytes}-")
    else:
        print(f"Initiating fresh download: {meta['filename']} ({expected_size / 1024 / 1024:.2f} MB)...")

    bytes_this_run = 0
    start_time = time.perf_counter()
    last_report = start_time

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0), follow_redirects=True) as client:
            with client.stream("GET", url, headers=headers) as response:
                if is_resuming:
                    if response.status_code == 200:
                        print("Server ignored Range request (HTTP 200). Aborting to protect partial file.", file=sys.stderr)
                        return False
                    elif response.status_code != 206:
                        print(f"Server returned HTTP {response.status_code}. Aborting.", file=sys.stderr)
                        return False
                    print(f"Server accepted resume: HTTP 206 (Content-Range: {response.headers.get('content-range')})")
                else:
                    if response.status_code != 200:
                        print(f"Server returned HTTP {response.status_code}. Aborting.", file=sys.stderr)
                        return False

                with open(archive_path, open_mode) as f:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        chunk_len = len(chunk)
                        bytes_this_run += chunk_len

                        now = time.perf_counter()
                        if (now - last_report) >= 2.0:
                            current_total = existing_bytes + bytes_this_run
                            pct = (current_total / expected_size) * 100.0
                            remaining = expected_size - current_total
                            elapsed = now - start_time
                            speed = (bytes_this_run / (1024 * 1024)) / elapsed if elapsed > 0 else 0.0
                            eta = remaining / (speed * 1024 * 1024) if speed > 0 else 0.0

                            print(
                                f"Downloaded: {current_total / 1024 / 1024:.1f} MB / {expected_size / 1024 / 1024:.1f} MB "
                                f"| Remaining: {remaining / 1024 / 1024:.1f} MB "
                                f"| {pct:.1f}% "
                                f"| Speed: {speed:.2f} MB/s "
                                f"| ETA: {eta:.0f}s"
                            )
                            last_report = now

        print(f"\nDownload finished: {bytes_this_run:,} bytes received during this session.")
        return verify_archive(archive_path, expected_size, expected_sha256)

    except KeyboardInterrupt:
        print("\nDownload interrupted by user. Partial file preserved.")
        return False
    except Exception as e:
        print(f"\nNetwork error: {e}. Partial file preserved.", file=sys.stderr)
        return False


def extract_archive(file_key: str):
    meta = FILES_META[file_key]
    archive_path = meta["archive_path"]
    extracted_target = DATASET_DIR / "extracted" / Path(meta["filename"]).stem
    extracted_target.mkdir(parents=True, exist_ok=True)

    print(f"\nExtracting {archive_path.name} to {extracted_target}...")
    with zipfile.ZipFile(archive_path, "r") as z:
        for member in z.infolist():
            target_path = (extracted_target / member.filename).resolve()
            try:
                target_path.relative_to(extracted_target.resolve())
            except ValueError:
                print(f"SECURITY ALERT: Unsafe member path: {member.filename}", file=sys.stderr)
                sys.exit(1)
        z.extractall(extracted_target)
    print("  [OK] Extraction complete.")


def main():
    parser = argparse.ArgumentParser(description="Downloader for Mendeley Corrosion Segmentation dataset (10.17632/kcyn4nhv2c.1)")
    parser.add_argument("--include-complete-database", action="store_true", help="Also download the 2.2GB complete database")
    parser.add_argument("--extract", action="store_true", help="Extract archives after verification")
    parser.add_argument("--verify-only", action="store_true", help="Verify existing archives only")
    args = parser.parse_args()

    files_to_process = ["labeled_images"]
    if args.include_complete_database:
        files_to_process.append("complete_database")

    all_success = True
    for key in files_to_process:
        if args.verify_only:
            ok = verify_archive(FILES_META[key]["archive_path"], FILES_META[key]["expected_size"], FILES_META[key]["expected_sha256"])
        else:
            ok = download_file(key)
            if ok and args.extract:
                extract_archive(key)
        if not ok:
            all_success = False

    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
