# -*- coding: utf-8 -*-
"""Agent Search Lite — Additional Free Backends.

Reddit JSON API, Yahoo Finance, Image search, More package registries,
News aggregation, Fallback search engines.

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

logger = logging.getLogger(__name__)

REDDIT_JSON = "https://www.reddit.com"
REDDIT_SEARCH = "https://www.reddit.com/search.json"
YAHOO_FINANCE = "https://query1.finance.yahoo.com/v8/finance/chart"
UNPLASH_API = "https://api.unsplash.com"
PEXELS_API = "https://api.pexels.com/v1"
CRATES_IO = "https://crates.io/api/v1"
PACKAGIST = "https://packagist.org"
NPM_RSS = "https://registry.npmjs.org/-/v1/search"
PYPI_SIMPLE = "https://pypi.org/simple"
DOCKERHUB_V2 = "https://hub.docker.com/v2"
OPENLIBRARY_COVERS = "https://covers.openlibrary.org"
LIBRARY_IO = "https://libraries.io/api"
FRESHRSS = "https://freshrss.org"
MINIFLUX = "https://miniflux.app"


# ---------------------------------------------------------------------------
# Reddit JSON API
# ---------------------------------------------------------------------------

def reddit_search(query: str, limit: int = 10, subreddit: str = None) -> Optional[Dict[str, Any]]:
    """Search Reddit via JSON API (no auth required)."""
    try:
        url = f"{REDDIT_JSON}/search.json"
        if subreddit:
            url = f"{REDDIT_JSON}/r/{subreddit}/search.json"
        
        resp = httpx.get(
            url,
            params={
                "q": query,
                "limit": limit,
                "sort": "relevance",
                "restrict_sr": "false",
            },
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        
        posts = data.get("data", {}).get("children", [])
        if not posts:
            return None
        
        results = []
        for post in posts[:limit]:
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            permalink = post_data.get("permalink", "")
            subreddit_name = post_data.get("subreddit", "")
            score = post_data.get("score", 0)
            comments = post_data.get("num_comments", 0)
            created = post_data.get("created_utc", 0)
            selftext = post_data.get("selftext", "")[:500] if post_data.get("selftext") else ""
            url = post_data.get("url", "")
            
            results.append({
                "title": title,
                "url": f"https://reddit.com{permalink}" if permalink else url,
                "description": selftext or f"r/{subreddit_name} | Score: {score} | Comments: {comments}",
                "score": score,
                "subreddit": subreddit_name,
                "created": created,
                "source": "reddit",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Reddit search failed: %s", exc)
    return None


def reddit_subreddit_posts(subreddit: str, limit: int = 10, sort: str = "hot") -> Optional[Dict[str, Any]]:
    """Get posts from a subreddit."""
    try:
        resp = httpx.get(
            f"{REDDIT_JSON}/r/{subreddit}/{sort}.json",
            params={"limit": limit},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        posts = data.get("data", {}).get("children", [])
        if not posts:
            return None
        
        results = []
        for post in posts[:limit]:
            post_data = post.get("data", {})
            results.append({
                "title": post_data.get("title", ""),
                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                "description": post_data.get("selftext", "")[:500] if post_data.get("selftext") else "",
                "score": post_data.get("score", 0),
                "comments": post_data.get("num_comments", 0),
                "source": "reddit",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Reddit posts failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------

def yahoo_finance_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Yahoo Finance for stock quotes."""
    try:
        resp = httpx.get(
            f"https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": query, "quotesCount": limit, "newsCount": 0},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        quotes = data.get("quotes", [])
        if not quotes:
            return None
        
        results = []
        for quote in quotes[:limit]:
            symbol = quote.get("symbol", "")
            name = quote.get("longname") or quote.get("shortname", "")
            exchange = quote.get("exchange", "")
            type_disp = quote.get("quoteType", "")
            market = quote.get("market", "")
            
            results.append({
                "title": f"{name} ({symbol})",
                "url": f"https://finance.yahoo.com/quote/{symbol}",
                "description": f"{exchange} | {type_disp} | {market}",
                "symbol": symbol,
                "exchange": exchange,
                "type": type_disp,
                "source": "yahoo_finance",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Yahoo Finance search failed: %s", exc)
    return None


def yahoo_finance_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Get real-time stock quote from Yahoo Finance."""
    try:
        resp = httpx.get(
            f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "1d"},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        result = data.get("chart", {}).get("result", [{}])[0] if data.get("chart", {}).get("result") else {}
        meta = result.get("meta", {})
        
        return {
            "symbol": meta.get("symbol", ""),
            "currency": meta.get("currency", ""),
            "regularMarketPrice": meta.get("regularMarketPrice", 0),
            "previousClose": meta.get("previousClose", 0),
            "regularMarketDayHigh": meta.get("regularMarketDayHigh", 0),
            "regularMarketDayLow": meta.get("regularMarketDayLow", 0),
            "regularMarketVolume": meta.get("regularMarketVolume", 0),
            "exchangeName": meta.get("exchangeName", ""),
            "instrumentType": meta.get("instrumentType", ""),
        }
    
    except Exception as exc:
        logger.debug("Yahoo Finance quote failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Image Search
# ---------------------------------------------------------------------------

def unsplash_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Unsplash for free images (no key for basic search)."""
    try:
        resp = httpx.get(
            "https://unsplash.com/napi/search/photos",
            params={"query": query, "per_page": limit, "order_by": "relevant"},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        results_list = data.get("results", [])
        if not results_list:
            return None
        
        results = []
        for i, photo in enumerate(results_list[:limit]):
            urls = photo.get("urls", {})
            user = photo.get("user", {})
            
            results.append({
                "title": photo.get("description") or photo.get("alt_description") or f"Photo by {user.get('name', '')}",
                "url": photo.get("links", {}).get("html", ""),
                "description": f"By {user.get('name', '')} | Downloads: {photo.get('downloads', 0)}",
                "thumb": urls.get("small", ""),
                "full": urls.get("regular", ""),
                "source": "unsplash",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Unsplash search failed: %s", exc)
    return None


def pexels_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Pexels for free images."""
    try:
        resp = httpx.get(
            f"{PEXELS_API}/search",
            params={"query": query, "per_page": limit},
            headers={
                "User-Agent": ua_rotator.get(),
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        photos = data.get("photos", [])
        if not photos:
            return None
        
        results = []
        for i, photo in enumerate(photos[:limit]):
            src = photo.get("src", {})
            results.append({
                "title": photo.get("alt", f"Photo by {photo.get('photographer', '')}"),
                "url": photo.get("url", ""),
                "description": f"By {photo.get('photographer', '')}",
                "thumb": src.get("medium", ""),
                "full": src.get("original", ""),
                "source": "pexels",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Pexels search failed: %s", exc)
    return None


def pixabay_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Pixabay for free images (no key for basic search)."""
    try:
        resp = httpx.get(
            "https://pixabay.com/api/",
            params={
                "key": "47279345-3c6e2d9a4d2c4e8f1b6e7d9c3",
                "q": query,
                "per_page": limit,
                "image_type": "photo",
            },
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        hits = data.get("hits", [])
        if not hits:
            return None
        
        results = []
        for i, hit in enumerate(hits[:limit]):
            results.append({
                "title": hit.get("tags", f"Image by {hit.get('user', '')}"),
                "url": hit.get("pageURL", ""),
                "description": f"By {hit.get('user', '')} | Views: {hit.get('views', 0)}",
                "thumb": hit.get("webformatURL", ""),
                "full": hit.get("largeImageURL", ""),
                "source": "pixabay",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Pixabay search failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# More Package Registries
# ---------------------------------------------------------------------------

def crates_io_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search crates.io for Rust packages."""
    try:
        resp = httpx.get(
            f"{CRATES_IO}/crates",
            params={"q": query, "per_page": limit},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        crates = data.get("crates", [])
        if not crates:
            return None
        
        results = []
        for i, crate in enumerate(crates[:limit]):
            results.append({
                "title": crate.get("name", ""),
                "url": f"https://crates.io/crates/{crate.get('name', '')}",
                "description": crate.get("description", "")[:300],
                "version": crate.get("newest_version", ""),
                "downloads": crate.get("downloads", 0),
                "source": "crates_io",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("crates.io search failed: %s", exc)
    return None


def packagist_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Packagist for PHP packages."""
    try:
        resp = httpx.get(
            f"{PACKAGIST}/search.json",
            params={"q": query, "per_page": limit},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        results_list = data.get("results", [])
        if not results_list:
            return None
        
        results = []
        for i, pkg in enumerate(results_list[:limit]):
            results.append({
                "title": pkg.get("name", ""),
                "url": pkg.get("url", ""),
                "description": pkg.get("description", "")[:300],
                "downloads": pkg.get("downloads", 0),
                "favers": pkg.get("favers", 0),
                "source": "packagist",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Packagist search failed: %s", exc)
    return None


def go_pkg_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Go packages."""
    try:
        resp = httpx.get(
            "https://pkg.go.dev/search",
            params={"q": query, "limit": limit},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_go_pkg_results(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Go pkg search failed: %s", exc)
    return None


def _parse_go_pkg_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Go pkg search results."""
    results = []
    
    pattern = re.compile(
        r'<a[^>]*class="[^"]*SearchSnippet[^"]*"[^>]*href="([^"]*)"[^>]*>.*?<h2[^>]*>(.*?)</h2>.*?<p[^>]*class="[^"]*SearchSnippet-synopsis[^"]*"[^>]*>(.*?)</p>',
        re.DOTALL | re.IGNORECASE,
    )
    
    matches = pattern.findall(html)
    
    for i, (url, title, synopsis) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        synopsis = re.sub(r'<[^>]+>', '', synopsis).strip()
        
        if url and title:
            results.append({
                "title": title,
                "url": f"https://pkg.go.dev{url}" if url.startswith("/") else url,
                "description": synopsis,
                "source": "go_pkg",
                "position": i + 1,
            })
    
    return results


# ---------------------------------------------------------------------------
# News Aggregation
# ---------------------------------------------------------------------------

def hacker_news_latest(limit: int = 10) -> Optional[Dict[str, Any]]:
    """Get latest Hacker News stories."""
    try:
        resp = httpx.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        ids = resp.json()[:limit]
        
        results = []
        for i, story_id in enumerate(ids):
            try:
                story_resp = httpx.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    headers={"User-Agent": _UA},
                    timeout=10,
                )
                story_resp.raise_for_status()
                story = story_resp.json()
                
                results.append({
                    "title": story.get("title", ""),
                    "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "description": f"Score: {story.get('score', 0)} | Comments: {story.get('descendants', 0)}",
                    "score": story.get("score", 0),
                    "by": story.get("by", ""),
                    "source": "hackernews_latest",
                    "position": len(results) + 1,
                })
            except Exception:
                continue
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("HN latest failed: %s", exc)
    return None


def lobsters_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Lobste.rs (tech news aggregator)."""
    try:
        resp = httpx.get(
            "https://lobste.rs/search",
            params={"q": query, "what": "stories", "order": "relevance"},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_lobsters_results(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Lobsters search failed: %s", exc)
    return None


def _parse_lobsters_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Lobsters search HTML."""
    results = []
    
    pattern = re.compile(
        r'<a[^>]*class="[^"]*url[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )
    
    matches = pattern.findall(html)
    
    for i, (url, title, desc) in enumerate(matches[:limit]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        desc = re.sub(r'<[^>]+>', '', desc).strip()
        
        if url and title:
            results.append({
                "title": title,
                "url": url,
                "description": desc[:300],
                "source": "lobsters",
                "position": i + 1,
            })
    
    return results


# ---------------------------------------------------------------------------
# Alternative Search Engines
# ---------------------------------------------------------------------------

def mojeek_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Search Mojeek (independent search engine)."""
    try:
        resp = httpx.get(
            "https://www.mojeek.com/search",
            params={"q": query, "s": "0", "fmt": "html"},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_mojeek_results(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Mojeek search failed: %s", exc)
    return None


def _parse_mojeek_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Mojeek search HTML."""
    results = []
    
    pattern = re.compile(
        r'<a[^>]*class="[^"]*ob[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<p[^>]*class="[^"]*s[^"]*"[^>]*>(.*?)</p>',
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
                "source": "mojeek",
                "position": i + 1,
            })
    
    return results


def qwant_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Search Qwant (privacy search engine)."""
    try:
        resp = httpx.get(
            "https://www.qwant.com/",
            params={"q": query, "t": "web", "safesearch": 0},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        
        html = resp.text
        results = _parse_qwant_results(html, limit)
        
        if results:
            return {"success": True, "data": {"web": results}}
    
    except Exception as exc:
        logger.debug("Qwant search failed: %s", exc)
    return None


def _parse_qwant_results(html: str, limit: int) -> List[Dict[str, Any]]:
    """Parse Qwant search HTML."""
    results = []
    
    pattern = re.compile(
        r'<a[^>]*class="[^"]*[^"]*"[^>]*href="(https?://[^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?<p[^>]*>(.*?)</p>',
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
                "source": "qwant",
                "position": i + 1,
            })
    
    return results
