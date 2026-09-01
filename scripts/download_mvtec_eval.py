import hashlib
import os
import tarfile
from pathlib import Path
import httpx

DATASET_DIR = Path("data/raw/mvtec_ad")
EVAL_ARCHIVE = DATASET_DIR / "mvtec_ad_evaluation.tar.xz"
EVAL_URL = "https://www.mydrive.ch/shares/150450/bb24b914a28ddd2b5e35bd53d23177cd/download/439517473-1665675012/mvtec_ad_evaluation.tar.xz"


def download_and_extract_eval():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}
    print(f"Downloading official MVTec AD evaluation package from {EVAL_URL}...")
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
        r = client.get(EVAL_URL)
        if r.status_code == 200:
            with open(EVAL_ARCHIVE, "wb") as f:
                f.write(r.content)
            h = hashlib.sha256(r.content).hexdigest()
            print(f"Downloaded {len(r.content)} bytes. SHA-256: {h}")
            
            # Extract
            extracted_dir = DATASET_DIR / "evaluation"
            extracted_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(EVAL_ARCHIVE, "r:xz") as tar:
                tar.extractall(extracted_dir)
            print(f"Extracted evaluation code to {extracted_dir}")
            
            for item in extracted_dir.rglob("*"):
                if item.is_file():
                    print(" -", item.relative_to(DATASET_DIR))
        else:
            print(f"Download failed with status {r.status_code}")


if __name__ == "__main__":
    download_and_extract_eval()
