import httpx

def check_endpoints():
    endpoints = [
        "https://www.mydrive.ch/shares/38536/3830184030e49fe74747669442f0f282/download/420938113-1629952094/mvtec_anomaly_detection.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/bottle.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/metal_nut.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/screw.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/tile.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/grid.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/leather.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/wood.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/zipper.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/cable.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/capsule.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/carpet.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/hazelnut.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/pill.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/toothbrush.tar.xz",
        "https://huggingface.co/datasets/MVTec/mvtec-ad/resolve/main/transistor.tar.xz",
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
        for ep in endpoints:
            try:
                r = client.head(ep)
                print(f"[{r.status_code}] Size: {r.headers.get('content-length')} -> {ep.split('/')[-1]}")
            except Exception as e:
                print(f"[ERR] {ep.split('/')[-1]}: {e}")

if __name__ == "__main__":
    check_endpoints()
