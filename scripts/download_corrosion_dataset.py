import argparse
import hashlib
import os
import sys
import time
import zipfile
from pathlib import Path
import httpx

DATASET_DIR = Path("data/raw/corrosion_detection")
ARCHIVE_PATH = DATASET_DIR / "Corrosion_Data.zip"
EXPECTED_SHA256 = "f667aedcb6be8e25bdd3a454d106f9304953ad4eb5f267f6798b228be397c07a"
EXPECTED_TOTAL_SIZE = 662667730  # Exact Content-Length in bytes (~631.97 MB)
DOWNLOAD_URL = "https://data.mendeley.com/public-files/datasets/tbjn6p2gn9/files/c311d38e-f04d-41ff-a508-dba6b60cc07b/file_downloaded"


def get_remote_file_size() -> int:
    """Queries remote endpoint headers to determine full Content-Length."""
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
        r = client.head(DOWNLOAD_URL)
        if r.status_code == 200:
            length = r.headers.get("content-length")
            if length:
                return int(length)
    return EXPECTED_TOTAL_SIZE


def verify_archive_integrity(file_path: Path) -> bool:
    """Verifies SHA-256 and ZIP structural integrity of the downloaded archive."""
    if not file_path.exists():
        print(f"Error: Archive not found at {file_path}", file=sys.stderr)
        return False

    current_size = file_path.stat().st_size
    print(f"\n--- Verifying Archive Integrity ({file_path}) ---")
    print(f"  File size on disk: {current_size:,} bytes ({current_size / 1024 / 1024:.2f} MB)")
    
    if current_size != EXPECTED_TOTAL_SIZE:
        print(
            f"  WARNING: File size does not match expected ({EXPECTED_TOTAL_SIZE:,} bytes).",
            file=sys.stderr
        )
        return False

    # 1. Full SHA-256 calculation
    print("  Calculating full SHA-256 checksum across complete archive...")
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    calc_hash = h.hexdigest()
    print(f"  Calculated SHA-256: {calc_hash}")
    print(f"  Expected SHA-256:   {EXPECTED_SHA256}")

    if calc_hash != EXPECTED_SHA256:
        print("  ERROR: SHA-256 mismatch!", file=sys.stderr)
        return False
    print("  [OK] SHA-256 checksum verified successfully.")

    # 2. ZIP structure test
    print("  Testing ZIP archive structural integrity (testzip)...")
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            bad_file = z.testzip()
            if bad_file:
                print(f"  ERROR: Corrupted file inside ZIP: {bad_file}", file=sys.stderr)
                return False
            n_entries = len(z.infolist())
            print(f"  [OK] ZIP integrity check passed ({n_entries} entries in archive).")
            return True
    except Exception as e:
        print(f"  ERROR: Failed to open ZIP archive: {e}", file=sys.stderr)
        return False


def download_dataset_resumable() -> bool:
    """Performs a safe, resumable download using HTTP Range requests."""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    remote_total_size = get_remote_file_size()
    print(f"Target dataset: Mendeley 10.17632/tbjn6p2gn9.1 (Corrosion_Data.zip)")
    print(f"Expected remote size: {remote_total_size:,} bytes ({remote_total_size / 1024 / 1024:.2f} MB)")

    existing_bytes = 0
    if ARCHIVE_PATH.exists():
        existing_bytes = ARCHIVE_PATH.stat().st_size
        print(f"Found existing local file: {existing_bytes:,} bytes ({existing_bytes / 1024 / 1024:.2f} MB)")

    if existing_bytes == remote_total_size:
        print("Local file size matches expected total size. Verifying integrity...")
        return verify_archive_integrity(ARCHIVE_PATH)

    if existing_bytes > remote_total_size:
        print(
            f"ERROR: Local file size ({existing_bytes:,} bytes) exceeds remote size "
            f"({remote_total_size:,} bytes). Inconsistent state, aborting.",
            file=sys.stderr
        )
        return False

    request_headers = {
        "User-Agent": "Mozilla/5.0",
    }
    is_resuming = existing_bytes > 0

    if is_resuming:
        request_headers["Range"] = f"bytes={existing_bytes}-"
        print(f"Initiating resume request: Range: bytes={existing_bytes}-")
        open_mode = "ab"
    else:
        print("Initiating full download from byte 0...")
        open_mode = "wb"

    bytes_downloaded_this_run = 0
    start_time = time.perf_counter()
    last_report_time = start_time

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0), follow_redirects=True) as client:
            with client.stream("GET", DOWNLOAD_URL, headers=request_headers) as response:
                if is_resuming:
                    if response.status_code == 200:
                        print(
                            "ERROR: Server responded with HTTP 200 instead of HTTP 206 Partial Content. "
                            "Server ignored Range header. Aborting to protect existing partial file.",
                            file=sys.stderr
                        )
                        return False
                    elif response.status_code != 206:
                        print(
                            f"ERROR: Server returned unexpected status code {response.status_code}. "
                            "Aborting to protect existing partial file.",
                            file=sys.stderr
                        )
                        return False
                    print(f"Server accepted resume: HTTP 206 Partial Content (Content-Range: {response.headers.get('content-range')})")
                else:
                    if response.status_code != 200:
                        print(f"ERROR: Download returned HTTP {response.status_code}", file=sys.stderr)
                        return False

                with open(ARCHIVE_PATH, open_mode) as f:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        chunk_len = len(chunk)
                        bytes_downloaded_this_run += chunk_len
                        
                        now = time.perf_counter()
                        if (now - last_report_time) >= 2.0:
                            current_total = existing_bytes + bytes_downloaded_this_run
                            pct = (current_total / remote_total_size) * 100.0
                            remaining_bytes = remote_total_size - current_total
                            elapsed = now - start_time
                            speed = (bytes_downloaded_this_run / (1024 * 1024)) / elapsed if elapsed > 0 else 0.0
                            eta_sec = (remaining_bytes / (speed * 1024 * 1024)) if speed > 0 else 0.0
                            
                            print(
                                f"Downloaded: {current_total / 1024 / 1024:.1f} MB / {remote_total_size / 1024 / 1024:.1f} MB "
                                f"| Remaining: {remaining_bytes / 1024 / 1024:.1f} MB "
                                f"| {pct:.1f}% "
                                f"| Speed: {speed:.2f} MB/s "
                                f"| ETA: {eta_sec:.0f}s"
                            )
                            last_report_time = now

        print(f"\nDownload finished successfully.")
        print(f"  Bytes downloaded during this run: {bytes_downloaded_this_run:,} bytes ({bytes_downloaded_this_run / 1024 / 1024:.2f} MB)")
        print(f"  Final file size on disk: {ARCHIVE_PATH.stat().st_size:,} bytes")
        return verify_archive_integrity(ARCHIVE_PATH)

    except KeyboardInterrupt:
        print("\nDownload interrupted by user (Ctrl+C). Partial file preserved for future resume.")
        return False
    except Exception as e:
        print(f"\nNetwork/Download error: {e}. Partial file preserved for future resume.", file=sys.stderr)
        return False


def extract_archive():
    """Extracts the verified archive to the dataset folder."""
    if not ARCHIVE_PATH.exists():
        print(f"Error: Archive {ARCHIVE_PATH} does not exist.", file=sys.stderr)
        return
    print(f"Extracting {ARCHIVE_PATH} to {DATASET_DIR}...")
    with zipfile.ZipFile(ARCHIVE_PATH, "r") as zip_ref:
        zip_ref.extractall(DATASET_DIR)
    print("Extraction complete.")


def main():
    parser = argparse.ArgumentParser(description="Resumable downloader for Mendeley Corrosion Dataset")
    parser.add_argument("--extract", action="store_true", help="Extract archive after successful verification")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing archive on disk")
    args = parser.parse_args()

    if args.verify_only:
        success = verify_archive_integrity(ARCHIVE_PATH)
    else:
        success = download_dataset_resumable()
        if success and args.extract:
            extract_archive()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
