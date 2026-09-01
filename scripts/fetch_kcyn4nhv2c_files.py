import httpx
import json
import time

def fetch_files():
    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://data.mendeley.com/api/datasets/kcyn4nhv2c/files"
    for attempt in range(5):
        try:
            with httpx.Client(timeout=20.0, headers=headers) as client:
                r = client.get(url)
                if r.status_code == 200:
                    files = r.json()
                    print(f"Successfully retrieved {len(files)} files metadata from Mendeley API:")
                    print(json.dumps(files, indent=2))
                    return files
                else:
                    print(f"Attempt {attempt+1}: Status {r.status_code}")
        except Exception as e:
            print(f"Attempt {attempt+1} error: {e}")
            time.sleep(2)
    return None

if __name__ == "__main__":
    fetch_files()
