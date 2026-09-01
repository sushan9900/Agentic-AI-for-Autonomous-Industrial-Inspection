import httpx
import re

def find_links():
    url = "https://www.mvtec.com/research-teaching/datasets/mvtec-ad"
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        # Find all forms or buttons or links
        forms = re.findall(r'<form[^>]*>(.*?)</form>', r.text, re.DOTALL)
        print(f"Forms on page: {len(forms)}")
        for f in forms:
            print("Form snippet:", f[:300])

        links = re.findall(r'<a[^>]+href=["\'](.*?)["\'][^>]*>(.*?)</a>', r.text, re.DOTALL)
        for h, t in links:
            txt = " ".join(t.split())
            if any(k in txt.lower() for k in ["download", "data", "eval", "code", "image", "tar"]):
                print(f"Link: '{txt}' -> {h}")

if __name__ == "__main__":
    find_links()
