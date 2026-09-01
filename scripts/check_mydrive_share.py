import httpx

def check_share():
    url = "https://www.mydrive.ch/shares/150450/bb24b914a28ddd2b5e35bd53d23177cd/download/439517473-1665675012/mvtec_ad_evaluation.tar.xz"
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        r = client.head(url)
        print("Evaluation tarball HTTP status:", r.status_code)
        print("Content-Length:", r.headers.get("content-length"))
        print("Content-Type:", r.headers.get("content-type"))

if __name__ == "__main__":
    check_share()
