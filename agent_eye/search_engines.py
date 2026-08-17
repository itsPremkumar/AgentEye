# -*- coding: utf-8 -*-
"""Agent Search Lite — Google Search & Enhanced DDG Backends.

Google search scraper (OpenSERP pattern), enhanced DDG, parallel search.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

from agent_eye.throttle import ua_rotator

# Active search language (set per search() call). Backends read this so a
# requested language (e.g. "ta", "hi") is forwarded to the upstream service
# instead of always defaulting to English. Empty string -> service default.
_SEARCH_LANG = ""


def set_search_lang(lang: str) -> None:
    """Set the language used by subsequent scraper/ddgs calls ('' = default)."""
    global _SEARCH_LANG
    _SEARCH_LANG = (lang or "").strip()


def get_search_lang() -> str:
    return _SEARCH_LANG


def _accept_language() -> str:
    """Build an Accept-Language header from the active search language."""
    return f"{_SEARCH_LANG};q=0.9, en;q=0.8" if _SEARCH_LANG else "en-US,en;q=0.9"


logger = logging.getLogger(__name__)

GOOGLE_SEARCH = "https://www.google.com/search"
DUCKDUCKGO_HTML = "https://html.duckduckgo.com/html/"
DUCKDUCKGO_API = "https://api.duckduckgo.com"
BING_SEARCH = "https://www.bing.com/search"
BRAVE_SEARCH = "https://search.brave.com/search"
START_PAGE = "https://www.startpage.com/sp/search"
YAHOO_SEARCH = "https://search.yahoo.com/search"
Ecosia_SEARCH = "https://www.ecosia.org/search"

# HTML scrapers (Google/Bing/Brave/StartPage/Yahoo/Ecosia/DDG) break whenever the
# search engines change their markup or serve a JS/consent page. When a scraper
# returns nothing, fall back transparently to the `ddgs` library (DuckDuckGo
# HTML, no API key) so the source still yields results. The fallback is tagged
# `fallback_via="ddgs"` so callers know the result came from the fallback.
def _ddgs_fallback(query: str, limit: int, source: str) -> Optional[Dict[str, Any]]:
    """Best-effort fallback: query DuckDuckGo via the `ddgs` library.

    Returns results tagged with the *original* source so downstream dedup still
    works, but also marks `fallback_via="ddgs"` for transparency. Returns None if
    `ddgs` is unavailable or yields nothing.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        logger.debug("ddgs not installed; skipping %s fallback", source)
        return None
    try:
        results: List[Dict[str, Any]] = []
        with DDGS(timeout=10) as client:
            kwargs = {"max_results": limit}
            if _SEARCH_LANG:
                kwargs["region"] = _SEARCH_LANG
            for i, hit in enumerate(client.text(query, **kwargs)):
                if i >= limit:
                    break
                url = str(hit.get("href") or hit.get("url") or "")
                title = str(hit.get("title", ""))
                if not url or not title:
                    continue
                results.append({
                    "title": title,
                    "url": url,
                    "description": str(hit.get("body", ""))[:300],
                    "source": source,
                    "position": i + 1,
                    "fallback_via": "ddgs",
                })
        if results:
            return {"success": True, "data": {"web": results}, "fallback_via": "ddgs"}
    except Exception as exc:
        logger.debug("%s ddgs fallback failed: %s", source, exc)
    return None


# ---------------------------------------------------------------------------
# Google Search Scraper (OpenSERP pattern)
# ---------------------------------------------------------------------------

def google_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Scrape Google search results (no API key required).

    Uses the OpenSERP pattern: scrape Google's public search page
    and parse results into structured JSON.
    """
    try:
        resp = httpx.get(
            GOOGLE_SEARCH,
            params={"q": query, "num": limit, "hl": "en"},
            headers={
                "User-Agent": ua_rotator.get(),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": _accept_language(),
            },
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()

        html = resp.text
        results = _parse_google_results(html, limit)

        if results:
            return {"success": True, "data": {"web": results}}

    except Exception as exc:
        logger.debug("Google search failed: %s", exc)

    # Markup changed / consent page / blocked -> fall back to ddgs
    return _ddgs_fallback(query, limit, "google")


def _parse_google_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Google search HTML for results."""
    results = []

    # Pattern for organic search results
    # Google's structure changes frequently, so we use multiple patterns
    patterns = [
        # Standard result pattern
        re.compile(
            r'<div class="[^"]*g[^"]*">.*?<a[^>]*href="(/url\?q=|)(https?://[^"&]+)[^"]*"[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?<span[^>]*>(.*?)</span>',
            re.DOTALL | re.IGNORECASE,
        ),
        # Alternative pattern
        re.compile(
            r'<a[^>]*href="(/url\?q=|)(https?://[^"&]+)"[^>]*>.*?<div[^>]*class="[^"]*[^>]*>(.*?)</div>',
            re.DOTALL | re.IGNORECASE,
        ),
    ]

    seen_urls = set()

    for pattern in patterns:
        matches = pattern.findall(html)
        for match in matches:
            if len(match) >= 3:
                url = match[1] if match[1] else urllib.parse.unquote(match[0].replace("/url?q=", ""))
                title = re.sub(r'<[^>]+>', '', match[2] if len(match) > 2 else "").strip()
                snippet = re.sub(r'<[^>]+>', '', match[3] if len(match) > 3 else "").strip()

                if url and title and url not in seen_urls:
                    seen_urls.add(url)
                    results.append({
                        "title": title,
                        "url": url,
                        "description": snippet[:300],
                        "source": "google",
                        "position": len(results) + 1,
                    })

                    if len(results) >= limit:
                        break

        if results:
            break

    return results[:limit]


# ---------------------------------------------------------------------------
# Enhanced DuckDuckGo
# ---------------------------------------------------------------------------

def duckduckgo_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Enhanced DuckDuckGo search with multiple fallback methods."""
    # Try HTML interface first
    result = _ddg_html_search(query, limit)
    if result:
        return result

    # Fall back to Jina Reader approach
    result = _ddg_jina_search(query, limit)
    if result:
        return result

    # Both HTML scraping paths failed -> fall back to ddgs
    return _ddgs_fallback(query, limit, "duckduckgo")


# ---------------------------------------------------------------------------
# DuckDuckGo News Search (dedicated news endpoint)
# ---------------------------------------------------------------------------

def duckduckgo_news_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Search DuckDuckGo's dedicated news endpoint.

    This is a different endpoint from text search — it returns recent
    headlines with source attribution and publication dates. Falls back
    to the ddgs library if scraping fails.
    """
    try:
        # Try DuckDuckGo Lite news
        resp = httpx.get(
            "https://duckduckgo.com/",
            params={"q": query, "kl": "us-en", "iar": "news"},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
        results = _parse_ddg_news_results(resp.text, limit)
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("DDG news HTML search failed: %s", exc)

    # Fallback to ddgs library
    return _ddgs_news_fallback(query, limit)


def _parse_ddg_news_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse DuckDuckGo news HTML results."""
    results = []
    pattern = re.compile(
        r'<a[^>]*class="[^\"]*result__a[^\"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<a[^>]*class="[^\"]*result__snippet[^\"]*"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    matches = pattern.findall(html)
    for i, (url, title, snippet) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        if url and title:
            results.append({
                "title": title,
                "url": url,
                "description": snippet[:300],
                "source": "duckduckgo-news",
                "position": i + 1,
            })
    return results


def _ddgs_news_fallback(query: str, limit: int) -> Optional[Dict[str, Any]]:
    """Fallback: use the ddgs library's news() endpoint."""
    try:
        from ddgs import DDGS
    except ImportError:
        logger.debug("ddgs not installed; skipping news fallback")
        return None
    try:
        results = []
        with DDGS(timeout=10) as client:
            for i, hit in enumerate(client.news(query, max_results=limit)):
                if i >= limit:
                    break
                url = str(hit.get("url") or hit.get("href") or "")
                title = str(hit.get("title", ""))
                if not url or not title:
                    continue
                results.append({
                    "title": title,
                    "url": url,
                    "description": str(hit.get("body", ""))[:300],
                    "source": "duckduckgo-news",
                    "position": i + 1,
                    "date": str(hit.get("date", "")),
                    "source_name": str(hit.get("source", "")),
                })
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("ddgs news fallback failed: %s", exc)
    return None


def _ddg_html_search(query: str, limit: int) -> Optional[Dict[str, Any]]:
    """Search DuckDuckGo via HTML interface."""
    try:
        resp = httpx.get(
            DUCKDUCKGO_HTML,
            params={"q": query, "kl": "us-en"},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()

        html = resp.text
        results = _parse_ddg_results(html, limit)

        if results:
            return {"success": True, "data": {"web": results}}

    except Exception as exc:
        logger.debug("DDG HTML search failed: %s", exc)

    return None


def _parse_ddg_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse DuckDuckGo HTML results."""
    results = []

    # DDG result pattern
    pattern = re.compile(
        r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    matches = pattern.findall(html)

    for i, (url, title, snippet) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = re.sub(r'<[^+]+>', '', snippet).strip()

        if url and title:
            results.append({
                "title": title,
                "url": url,
                "description": snippet[:300],
                "source": "duckduckgo",
                "position": i + 1,
            })

    return results


def _ddg_jina_search(query: str, limit: int) -> Optional[Dict[str, Any]]:
    """Search DuckDuckGo via Jina Reader fallback."""
    try:
        ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        resp = httpx.get(
            f"https://r.jina.ai/{ddg_url}",
            headers={"User-Agent": ua_rotator.get(), "Accept": "text/plain"},
            timeout=30,
        )
        resp.raise_for_status()

        text = resp.text
        results = _parse_ddg_jina_results(text, limit)

        if results:
            return {"success": True, "data": {"web": results}}

    except Exception as exc:
        logger.debug("DDG Jina search failed: %s", exc)

    return None


def _parse_ddg_jina_results(text: str, limit: int) -> List[Dict[str, Any]]:
    """Parse DuckDuckGo results from Jina Reader output."""
    results = []

    # Parse markdown-formatted results
    pattern = re.compile(r'^## \[(.+?)\]\((.+?)\)$', re.MULTILINE)
    lines = text.split("\n")

    for i, line in enumerate(lines):
        match = pattern.match(line.strip())
        if match:
            title = match.group(1)
            url = match.group(2)

            # Skip DDG internal links
            if "duckduckgo.com" in url and "/html/" in url:
                continue

            # Get snippet from next lines
            snippet = ""
            for j in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith("[") and not next_line.startswith("!"):
                    snippet = next_line
                    break

            results.append({
                "title": title,
                "url": url,
                "description": snippet[:300],
                "source": "duckduckgo",
                "position": len(results) + 1,
            })

            if len(results) >= limit:
                break

    return results


# ---------------------------------------------------------------------------
# Bing Search
# ---------------------------------------------------------------------------

def bing_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Scrape Bing search results."""
    try:
        resp = httpx.get(
            BING_SEARCH,
            params={"q": query, "count": limit},
            headers={
                "User-Agent": ua_rotator.get(),
                "Accept-Language": _accept_language(),
            },
            timeout=15,
        )
        resp.raise_for_status()

        html = resp.text
        results = _parse_bing_results(html, limit)

        if results:
            return {"success": True, "data": {"web": results}}

    except Exception as exc:
        logger.debug("Bing search failed: %s", exc)

    return _ddgs_fallback(query, limit, "bing")


def _parse_bing_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Bing search HTML."""
    results = []

    pattern = re.compile(
        r'<li class="b_algo">.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>',
        re.DOTALL | re.IGNORECASE,
    )

    matches = pattern.findall(html)

    for i, (url, title, snippet) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()

        if url and title:
            results.append({
                "title": title,
                "url": url,
                "description": snippet[:300],
                "source": "bing",
                "position": i + 1,
            })

    return results


# ---------------------------------------------------------------------------
# Brave Search
# ---------------------------------------------------------------------------

def brave_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Scrape Brave search results."""
    try:
        resp = httpx.get(
            BRAVE_SEARCH,
            params={"q": query, "source": "web"},
            headers={
                "User-Agent": ua_rotator.get(),
                "Accept-Language": _accept_language(),
            },
            timeout=15,
        )
        resp.raise_for_status()

        html = resp.text
        results = _parse_brave_results(html, limit)

        if results:
            return {"success": True, "data": {"web": results}}

    except Exception as exc:
        logger.debug("Brave search failed: %s", exc)

    return _ddgs_fallback(query, limit, "brave")


def _parse_brave_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Brave search HTML."""
    results = []

    pattern = re.compile(
        r'<a[^>]*class="[^"]*[^"]*"[^>]*href="(/l/|https?://[^"]+)"[^>]*>(.*?)</a>.*?<div[^>]*class="[^"]*snippet[^"]*"[^>]*>(.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )

    matches = pattern.findall(html)

    for i, (url, title, snippet) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()

        if url and title:
            full_url = f"https://search.brave.com{url}" if url.startswith("/l/") else url
            results.append({
                "title": title,
                "url": full_url,
                "description": snippet[:300],
                "source": "brave",
                "position": i + 1,
            })

    return results


# ---------------------------------------------------------------------------
# StartPage Search
# ---------------------------------------------------------------------------

def startpage_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Scrape StartPage search results (Google results, privacy-focused)."""
    try:
        resp = httpx.get(
            START_PAGE,
            params={"query": query, "cat": "web", "page": 1},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()

        html = resp.text
        results = _parse_startpage_results(html, limit)

        if results:
            return {"success": True, "data": {"web": results}}

    except Exception as exc:
        logger.debug("StartPage search failed: %s", exc)

    return _ddgs_fallback(query, limit, "startpage")


def _parse_startpage_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse StartPage search HTML."""
    results = []

    pattern = re.compile(
        r'<a[^>]*class="[^"]*result-title[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<p[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</p>',
        re.DOTALL | re.IGNORECASE,
    )

    matches = pattern.findall(html)

    for i, (url, title, snippet) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()

        if url and title:
            results.append({
                "title": title,
                "url": url,
                "description": snippet[:300],
                "source": "startpage",
                "position": i + 1,
            })

    return results


# ---------------------------------------------------------------------------
# Yahoo Search
# ---------------------------------------------------------------------------

def yahoo_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Scrape Yahoo search results."""
    try:
        resp = httpx.get(
            YAHOO_SEARCH,
            params={"p": query, "b": 1, "pz": limit},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()

        html = resp.text
        results = _parse_yahoo_results(html, limit)

        if results:
            return {"success": True, "data": {"web": results}}

    except Exception as exc:
        logger.debug("Yahoo search failed: %s", exc)

    return _ddgs_fallback(query, limit, "yahoo")


def _parse_yahoo_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Yahoo search HTML."""
    results = []

    pattern = re.compile(
        r'<a[^>]*class="[^"]*[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<p[^>]*class="[^"]*[^"]*"[^>]*>(.*?)</p>',
        re.DOTALL | re.IGNORECASE,
    )

    matches = pattern.findall(html)

    for i, (url, title, snippet) in enumerate(matches[:limit]):
        title = re.sub(r'<[^+]+>', '', title).strip()
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()

        if url and title:
            results.append({
                "title": title,
                "url": url,
                "description": snippet[:300],
                "source": "yahoo",
                "position": i + 1,
            })

    return results


# ---------------------------------------------------------------------------
# Ecosia Search
# ---------------------------------------------------------------------------

def ecosia_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Scrape Ecosia search results."""
    try:
        resp = httpx.get(
            Ecosia_SEARCH,
            params={"q": query},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()

        html = resp.text
        results = _parse_ecosia_results(html, limit)

        if results:
            return {"success": True, "data": {"web": results}}

    except Exception as exc:
        logger.debug("Ecosia search failed: %s", exc)

    return _ddgs_fallback(query, limit, "ecosia")


def _parse_ecosia_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Ecosia search HTML."""
    results = []

    pattern = re.compile(
        r'<a[^>]*class="[^"]*result-url[^"]*"[^>]*href="([^"]*)"[^>]*>.*?<h2[^>]*class="[^"]*result-title[^"]*"[^>]*>(.*?)</h2>.*?<p[^>]*class="[^"]*result-snippet[^"]*"[^>]*>(.*?)</p>',
        re.DOTALL | re.IGNORECASE,
    )

    matches = pattern.findall(html)

    for i, (url, title, snippet) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()

        if url and title:
            results.append({
                "title": title,
                "url": url,
                "description": snippet[:300],
                "source": "ecosia",
                "position": i + 1,
            })

    return results
