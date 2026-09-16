from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; BlogAppBot/1.0)"
MAX_TEXT_CHARS = 4000
MAX_IMAGES = 5


def scrape_url(url: str) -> dict:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        return {"url": url, "text": "", "images": []}

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    text = " ".join(soup.stripped_strings)[:MAX_TEXT_CHARS]

    images = []
    for img in soup.find_all("img", src=True):
        src = urljoin(url, img["src"])
        if src.startswith("http") and src not in images:
            images.append(src)
        if len(images) >= MAX_IMAGES:
            break

    return {"url": url, "text": text, "images": images}
