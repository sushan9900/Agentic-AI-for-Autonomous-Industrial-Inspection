import httpx

def check_mvtec_download():
    url = "https://www.mydrive.ch/shares/38536/3830184030e49fe74747669442f0f282/download/420938113-1629952094/mvtec_anomaly_detection.tar.xz"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
            r = client.head(url)
            print("Status:", r.status_code)
            print("Content-Type:", r.headers.get("content-type"))
            print("Content-Length:", r.headers.get("content-length"))
            print("Accept-Ranges:", r.headers.get("accept-ranges"))
    except Exception as e:
        print("Error checking MyDrive link:", e)

if __name__ == "__main__":
    check_mvtec_download()
