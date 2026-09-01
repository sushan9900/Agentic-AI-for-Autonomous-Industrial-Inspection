import httpx
import re

def parse_page():
    url = "https://www.mvtec.com/research-teaching/datasets/mvtec-ad"
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        print("Page fetch status:", r.status_code)
        # Search for download hrefs
        hrefs = re.findall(r'href=[\'"]([^\'"]+)[\'"]', r.text)
        print(f"Total hrefs found: {len(hrefs)}")
        for h in hrefs:
            if "mydrive.ch" in h or "tar.xz" in h or "download" in h.lower():
                print("  ->", h)

if __name__ == "__main__":
    parse_page()
