import httpx
import re

def parse_text():
    url = "https://www.mvtec.com/research-teaching/datasets/mvtec-ad"
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        # Search for sections around "Download"
        text = r.text
        for match in re.finditer(r'(?i)(dataset|download|license|terms)', text):
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 300)
            print("--- Snippet ---")
            print(text[start:end])
            print()

if __name__ == "__main__":
    parse_text()
