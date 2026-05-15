"""
Fetch and clean the text content of a web article.

Usage:
    python tools/fetch_article.py --url "https://example.com/article"

Prints cleaned article text to stdout. Caller handles saving/using the output.
"""

import argparse
import sys

# Force UTF-8 stdout on Windows to handle emoji and non-ASCII characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Tags whose content is noise, not article body
NOISE_TAGS = ["nav", "footer", "header", "aside", "script", "style", "noscript",
              "form", "button", "iframe", "ad", "advertisement"]


def fetch(url: str, timeout: int = 15) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR fetching {url}: {e}", file=sys.stderr)
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # Try article/main content containers first
    for selector in ["article", "main", '[role="main"]', ".article-body", ".post-content", ".entry-content"]:
        container = soup.select_one(selector)
        if container:
            text = container.get_text(separator="\n", strip=True)
            if len(text) > 200:
                return text

    # Fall back to body
    body = soup.find("body")
    if body:
        return body.get_text(separator="\n", strip=True)

    return soup.get_text(separator="\n", strip=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="URL of article to fetch")
    parser.add_argument("--max-chars", type=int, default=8000, help="Truncate output to N chars")
    args = parser.parse_args()

    text = fetch(args.url)
    if not text:
        sys.exit(1)

    print(text[:args.max_chars])


if __name__ == "__main__":
    main()
