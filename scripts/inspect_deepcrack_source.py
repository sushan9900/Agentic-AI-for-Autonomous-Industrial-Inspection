import httpx
import re

def check_deepcrack():
    url = "https://raw.githubusercontent.com/yhlleo/DeepCrack/master/README.md"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            print(f"GitHub README Status: {r.status_code}")
            if r.status_code == 200:
                print("README content preview:\n", r.text[:1500])
                # Find download links
                links = re.findall(r'https?://[^\s\)]+', r.text)
                print("\nLinks in README:")
                for l in links:
                    print(" -", l)
    except Exception as e:
        print(f"Error checking GitHub README: {e}")

if __name__ == "__main__":
    check_deepcrack()
