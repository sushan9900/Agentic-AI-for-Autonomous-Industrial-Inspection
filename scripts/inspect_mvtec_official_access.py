import httpx
from html.parser import HTMLParser

class MVTecHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_tag = None
        self.current_href = ""
        self.items = []
        self.in_relevant_tag = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attr_dict = dict(attrs)
        self.current_href = attr_dict.get("href", "")
        if tag in ["h1", "h2", "h3", "h4", "p", "a", "button", "span", "div"]:
            self.in_relevant_tag = True

    def handle_endtag(self, tag):
        self.current_tag = None
        self.in_relevant_tag = False

    def handle_data(self, data):
        data_clean = " ".join(data.split())
        if data_clean and self.in_relevant_tag:
            low = data_clean.lower()
            if any(k in low for k in ["download", "registration", "terms", "license", "agree", "dataset", "evaluation", "mydrive", "access", "form", "request"]):
                self.items.append((self.current_tag, data_clean, self.current_href))


def inspect():
    url = "https://www.mvtec.com/research-teaching/datasets/mvtec-ad"
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=25.0, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        print(f"Page Status: {r.status_code}")
        parser = MVTecHTMLParser()
        parser.feed(r.text)
        print(f"Found {len(parser.items)} relevant sections:")
        for tag, text, href in parser.items:
            print(f"  [{tag}] {text} | href: {href}")

if __name__ == "__main__":
    inspect()
