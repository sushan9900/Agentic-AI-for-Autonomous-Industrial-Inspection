import httpx
import re

url = "https://data.mendeley.com/datasets/tbjn6p2gn9/1"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
    r = client.get(url)

matches = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
if len(matches) > 4:
    print(matches[4])
