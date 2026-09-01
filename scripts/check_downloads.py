import httpx
import re
import json

def check_mendeley(dataset_id: str, version: int = 1):
    url = f"https://data.mendeley.com/datasets/{dataset_id}/{version}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        print(f"Dataset {dataset_id}/{version} HTTP status: {r.status_code}")
        # Look for __NEXT_DATA__ or json blobs
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', r.text)
        if match:
            data = json.loads(match.group(1))
            props = data.get("props", {}).get("pageProps", {}).get("dataset", {})
            title = props.get("name", "Unknown")
            files = props.get("files", [])
            print(f"Title: {title}")
            print(f"Files count: {len(files)}")
            for f in files:
                print(f" - {f.get('name')} ({f.get('size')} bytes) -> {f.get('download_url')}")
            return props
        else:
            print("No __NEXT_DATA__ script found.")
            return None

if __name__ == "__main__":
    print("Checking Ata et al (y4b5x4n38p)...")
    check_mendeley("y4b5x4n38p", 1)
    print("\nChecking Nash et al (437pmbp9bh)...")
    check_mendeley("437pmbp9bh", 1)
