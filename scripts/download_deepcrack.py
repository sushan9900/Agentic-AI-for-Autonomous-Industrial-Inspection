import argparse
import hashlib
import os
import sys
import time
import zipfile
from pathlib import Path
import httpx

DATASET_DIR = Path("data/raw/deepcrack")
ARCHIVE_PATH = DATASET_DIR / "DeepCrack.zip"
EXTRACTED_DIR = DATASET_DIR / "extracted"
EXPECTED_TOTAL_SIZE = 67708808  # 67,708,808 bytes (~64.57 MB)
DOWNLOAD_URL = "https://raw.githubusercontent.com/yhlleo/DeepCrack/master/dataset/DeepCrack.zip"


def verify_archive(archive_path: Path) -> bool:
    if not archive_path.exists():
        return False
    size = archive_path.stat().st_size
    print(f"\nVerifying {archive_path.name}...")
    print(f"  Size on disk: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
    if size != EXPECTED_TOTAL_SIZE:
        print(f"  Size mismatch: expected {EXPECTED_TOTAL_SIZE:,} bytes, found {size:,} bytes.", file=sys.stderr)
        return False

    print("  Calculating full SHA-256...")
    h = hashlib.sha256()
    with open(archive_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    calc_hash = h.hexdigest()
    print(f"  Calculated SHA-256: {calc_hash}")

    print("  Testing ZIP integrity...")
    try:
        with zipfile.ZipFile(archive_path, "r") as z:
            if z.testzip() is not None:
                print("  ZIP test failed!", file=sys.stderr)
                return False
            n_entries = len(z.infolist())
            print(f"  [OK] ZIP integrity check passed ({n_entries} entries).")
            return True
    except Exception as e:
        print(f"  ZIP open error: {e}", file=sys.stderr)
        return False


def download_deepcrack() -> bool:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    if ARCHIVE_PATH.exists() and ARCHIVE_PATH.stat().st_size == EXPECTED_TOTAL_SIZE:
        print("Archive already downloaded. Verifying...")
        return verify_archive(ARCHIVE_PATH)

    existing_bytes = 0
    if ARCHIVE_PATH.exists():
        existing_bytes = ARCHIVE_PATH.stat().st_size
        print(f"Found existing partial file: {existing_bytes:,} bytes")

    if existing_bytes > EXPECTED_TOTAL_SIZE:
        print("Error: Local file size exceeds expected size. Aborting.", file=sys.stderr)
        return False

    headers = {"User-Agent": "Mozilla/5.0"}
    is_resuming = existing_bytes > 0
    open_mode = "ab" if is_resuming else "wb"

    if is_resuming:
        headers["Range"] = f"bytes={existing_bytes}-"
        print(f"Initiating resume request: Range: bytes={existing_bytes}-")
    else:
        print(f"Initiating fresh download from {DOWNLOAD_URL} ({EXPECTED_TOTAL_SIZE / 1024 / 1024:.2f} MB)...")

    bytes_this_run = 0
    start_time = time.perf_counter()
    last_report = start_time

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0), follow_redirects=True) as client:
            with client.stream("GET", DOWNLOAD_URL, headers=headers) as response:
                if is_resuming:
                    if response.status_code == 200:
                        print("Server returned HTTP 200 (ignored Range). Aborting to protect partial file.", file=sys.stderr)
                        return False
                    elif response.status_code != 206:
                        print(f"Server returned HTTP {response.status_code}. Aborting.", file=sys.stderr)
                        return False
                    print(f"Server accepted resume: HTTP 206 (Content-Range: {response.headers.get('content-range')})")
                else:
                    if response.status_code != 200:
                        print(f"Server returned HTTP {response.status_code}. Aborting.", file=sys.stderr)
                        return False

                with open(ARCHIVE_PATH, open_mode) as f:
                    for chunk in response.iter_bytes(chunk_size=512 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        chunk_len = len(chunk)
                        bytes_this_run += chunk_len

                        now = time.perf_counter()
                        if (now - last_report) >= 2.0:
                            current_total = existing_bytes + bytes_this_run
                            pct = (current_total / EXPECTED_TOTAL_SIZE) * 100.0
                            remaining = EXPECTED_TOTAL_SIZE - current_total
                            elapsed = now - start_time
                            speed = (bytes_this_run / (1024 * 1024)) / elapsed if elapsed > 0 else 0.0
                            eta = remaining / (speed * 1024 * 1024) if speed > 0 else 0.0

                            print(
                                f"Downloaded: {current_total / 1024 / 1024:.1f} MB / {EXPECTED_TOTAL_SIZE / 1024 / 1024:.1f} MB "
                                f"| Remaining: {remaining / 1024 / 1024:.1f} MB "
                                f"| {pct:.1f}% "
                                f"| Speed: {speed:.2f} MB/s "
                                f"| ETA: {eta:.0f}s"
                            )
                            last_report = now

        print(f"\nDownload finished: {bytes_this_run:,} bytes received.")
        return verify_archive(ARCHIVE_PATH)

    except KeyboardInterrupt:
        print("\nDownload interrupted by user. Partial file preserved.")
        return False
    except Exception as e:
        print(f"\nNetwork error: {e}. Partial file preserved.", file=sys.stderr)
        return False


def extract_deepcrack():
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nExtracting {ARCHIVE_PATH.name} to {EXTRACTED_DIR}...")
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as z:
        for member in z.infolist():
            target = (EXTRACTED_DIR / member.filename).resolve()
            try:
                target.relative_to(EXTRACTED_DIR.resolve())
            except ValueError:
                print(f"SECURITY ALERT: Unsafe member path: {member.filename}", file=sys.stderr)
                sys.exit(1)
        z.extractall(EXTRACTED_DIR)
    print("  [OK] Extraction complete.")


def main():
    parser = argparse.ArgumentParser(description="Downloader and extractor for DeepCrack dataset")
    parser.add_argument("--extract", action="store_true", help="Extract archive after download & verification")
    parser.add_argument("--verify-only", action="store_true", help="Verify archive only")
    args = parser.parse_args()

    if args.verify_only:
        ok = verify_archive(ARCHIVE_PATH)
    else:
        ok = download_deepcrack()
        if ok and args.extract:
            extract_deepcrack()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
