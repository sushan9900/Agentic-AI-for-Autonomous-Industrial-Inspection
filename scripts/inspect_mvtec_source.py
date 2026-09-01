import httpx
import re

def check_mvtec():
    url = "https://www.mvtec.com/company/research/datasets/mvtec-ad"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            print(f"MVTec Status: {r.status_code}")
            if r.status_code == 200:
                print("Page title/header preview:")
                matches = re.findall(r'https?://[^\s"\'<>]+', r.text)
                print(f"Found {len(matches)} links on MVTec page.")
                for m in matches:
                    if any(k in m.lower() for k in ["download", "mydrive", "mvtec", "dataset", "tar.xz", "zip"]):
                        print(" -", m)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_mvtec()
