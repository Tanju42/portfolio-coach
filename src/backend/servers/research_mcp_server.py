import re

import httpx
from html.parser import HTMLParser
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("research")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

DDG_LITE = "https://lite.duckduckgo.com/lite/?q="


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.chunks.append(text)


def _extract_text(html: str, limit: int) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    joined = " ".join(extractor.chunks)
    joined = re.sub(r"\s+", " ", joined)
    return joined[:limit]


async def _ddg_search(query: str, count: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as client:
        response = await client.get(DDG_LITE, params={"q": query})
        response.raise_for_status()
        html = response.text
    results = []
    for match in re.finditer(r'<a rel="nofollow" class="result-link" href="([^"]+)"[^>]*>(.*?)</a>', html):
        url = match.group(1)
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if title:
            results.append({"title": title, "url": url})
        if len(results) >= count:
            break
    return results


async def _news_rss_search(query: str, count: int) -> list[dict]:
    import xml.etree.ElementTree as ET
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as client:
        response = await client.get("https://news.google.com/rss/search", params=params)
        response.raise_for_status()
    root = ET.fromstring(response.text)
    results = []
    for entry in root.iter("item"):
        title = (entry.findtext("title") or "").strip()
        link = (entry.findtext("link") or "").strip()
        pub = (entry.findtext("pubDate") or "").strip()
        source = entry.findtext("source") or "news"
        if title:
            results.append({"title": title, "url": link, "published": pub, "source": source})
        if len(results) >= count:
            break
    return results


@mcp.tool()
async def search_web(query: str, count: int = 5) -> dict:
    """Search the web: Google News RSS first (keyless, reliable), DuckDuckGo as fallback.
    Returns titles + URLs for the agent to fetch with fetch_page."""
    count = max(3, min(int(count), 10))
    results, provider = [], None
    try:
        results = await _news_rss_search(query, count)
        provider = "google-news-rss"
    except Exception:
        pass
    if not results:
        try:
            results = await _ddg_search(query, count)
            provider = "duckduckgo"
        except Exception:
            pass
    if not results:
        return {"results": [], "note": "no results; web search is unavailable right now"}
    return {"results": results, "provider": provider}


@mcp.tool()
async def fetch_page(url: str, limit: int = 4000) -> dict:
    """Fetch a web page and return its readable text (scripts/styles stripped), truncated."""
    if not url.startswith(("http://", "https://")):
        return {"error": "url must start with http(s)://"}
    limit = max(500, min(int(limit), 8000))
    try:
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception as error:
        return {"error": f"fetch failed: {error}"}
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type:
        return {"url": url, "text": response.text[:limit]}
    return {"url": url, "text": _extract_text(response.text, limit)}


if __name__ == "__main__":
    mcp.run()
