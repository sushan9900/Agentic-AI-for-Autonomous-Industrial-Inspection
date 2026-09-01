import httpx

def test_mirrors():
    candidates = [
        "https://www.mydrive.ch/shares/38536/3830184030e49fe74747669442f0f282/download/420937370-1629951498/bottle.tar.xz",
        "https://www.mydrive.ch/shares/38536/3830184030e49fe74747669442f0f282/download/420937637-1629951814/metal_nut.tar.xz",
        "https://www.mydrive.ch/shares/38536/3830184030e49fe74747669442f0f282/download/420938166-1629952174/screw.tar.xz",
        "https://www.mydrive.ch/shares/38536/3830184030e49fe74747669442f0f282/download/420938180-1629952210/tile.tar.xz",
        "https://www.mydrive.ch/shares/38536/3830184030e49fe74747669442f0f282/download/420937454-1629951590/grid.tar.xz",
        "https://raw.githubusercontent.com/skalskip/mvtec-anomaly-detection-dataset/master/README.md",
        "https://github.com/skalskip/mvtec-anomaly-detection-dataset/raw/master/README.md"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
        for url in candidates:
            try:
                r = client.head(url)
                print(f"[{r.status_code}] {url.split('/')[-1]}")
            except Exception as e:
                print(f"[ERR] {url.split('/')[-1]}: {e}")

if __name__ == "__main__":
    test_mirrors()
