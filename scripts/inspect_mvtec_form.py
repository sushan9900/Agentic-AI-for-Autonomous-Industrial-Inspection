import httpx
import re

def inspect_form():
    url = "https://www.mvtec.com/research-teaching/datasets/mvtec-ad"
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        # Find the form snippet around "Fill in the form"
        idx = r.text.find("Fill in the form")
        if idx != -1:
            snippet = r.text[idx-200:idx+2500]
            print("Form snippet around 'Fill in the form':")
            print(snippet)

if __name__ == "__main__":
    inspect_form()
