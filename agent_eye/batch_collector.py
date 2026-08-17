# -*- coding: utf-8 -*-
"""Agent Search Lite — Batch Website Data Collector.

Collects data from multiple URLs discovered via sitemaps,
RSS feeds, and Wayback Machine.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

import httpx

from agent_eye.extractors import smart_extract
from agent_eye.seo_extractor import extract_all_structured_data
from agent_eye.sitemap_parser import (
    discover_sitemaps,
    get_all_urls_from_sitemap,
    is_url_allowed,
    parse_robots_txt,
)
from agent_eye.throttle import ua_rotator
from agent_eye.exceptions import RobotsDisallowedError

logger = logging.getLogger(__name__)

# Fetch guards — protect the host machine (e.g. a 6GB laptop) from runaway
# downloads / redirect loops / thundering-herd crawls.
_MAX_FETCH_BYTES = 25 * 1024 * 1024  # 25 MB cap per response body
_MAX_REDIRECTS = 5
_FETCH_TIMEOUT = 30.0
_DOMAIN_CONCURRENCY = 2  # max simultaneous requests per domain

# Per-domain semaphore registry (module-level, shared across crawl/collect runs)
_domain_semaphores: Dict[str, "object"] = {}
_domain_semaphores_lock = None


def _domain_key(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc or url
    except Exception:
        return url


def _domain_semaphore(domain: str):
    """Return a bounded semaphore limiting concurrency for a given domain."""
    global _domain_semaphores_lock
    if _domain_semaphores_lock is None:
        import threading
        _domain_semaphores_lock = threading.Lock()
    with _domain_semaphores_lock:
        sem = _domain_semaphores.get(domain)
        if sem is None:
            sem = __import__("threading").Semaphore(_DOMAIN_CONCURRENCY)
            _domain_semaphores[domain] = sem
        return sem


def guarded_get(url: str, *, headers: Dict[str, str] = None, timeout: float = _FETCH_TIMEOUT) -> "object":
    """httpx GET with size + redirect guards.

    Streams the response and aborts if the body exceeds ``_MAX_FETCH_BYTES`` or
    redirects exceed ``_MAX_REDIRECTS``. Raises ``RobotsDisallowedError`` is NOT
    checked here (callers decide policy); this only enforces transport limits.
    """
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        max_redirects=_MAX_REDIRECTS,
        headers=headers or {"User-Agent": ua_rotator.get()},
    ) as client:
        resp = client.get(url)
        # Stream-read with a hard byte ceiling so a huge page can't OOM the host.
        chunks = []
        total = 0
        for chunk in resp.iter_bytes(chunk_size=64 * 1024):
            total += len(chunk)
            if total > _MAX_FETCH_BYTES:
                resp.close()
                raise httpx.DecodeError(
                    f"Response exceeded {_MAX_FETCH_BYTES} bytes; aborting fetch of {url}"
                )
            chunks.append(chunk)
        resp._content = b"".join(chunks)
        return resp


def assert_allowed(url: str, user_agent: str = "*") -> None:
    """Raise ``RobotsDisallowedError`` if robots.txt disallows ``url``."""
    try:
        if not is_url_allowed(url, user_agent):
            rule = ""
            try:
                parsed = urllib.parse.urlparse(url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                robots = parse_robots_txt(base)
                for agent in [user_agent, "*"]:
                    rules = robots.get("agents", {}).get(agent, {})
                    for dis in rules.get("disallow", []):
                        if (parsed.path or "/").startswith(dis):
                            rule = dis
                            break
            except Exception:
                pass
            raise RobotsDisallowedError(url, rule)
    except RobotsDisallowedError:
        raise
    except Exception:
        # If robots.txt can't be fetched/parsed, fail open (allow).
        return


# ---------------------------------------------------------------------------
# Batch URL Collector
# ---------------------------------------------------------------------------

def collect_from_sitemap(
    base_url: str,
    max_urls: int = 100,
    extract_content: bool = True,
    extract_seo: bool = True,
    max_workers: int = 5,
    delay: float = 0.5,
) -> Dict[str, Any]:
    """Collect data from all URLs in a website's sitemaps.
    
    Args:
        base_url: Website URL
        max_urls: Maximum URLs to process
        extract_content: Whether to extract markdown content
        extract_seo: Whether to extract SEO data
        max_workers: Number of parallel workers
        delay: Delay between requests
    
    Returns:
        {
            "base_url": "https://example.com",
            "total_urls": 50,
            "processed": 45,
            "failed": 5,
            "results": [
                {
                    "url": "https://example.com/page1",
                    "title": "...",
                    "content": "...",
                    "seo": {...}
                }
            ]
        }
    """
    result = {
        "base_url": base_url,
        "total_urls": 0,
        "processed": 0,
        "failed": 0,
        "results": [],
    }
    
    # Get all URLs from sitemaps
    urls = get_all_urls_from_sitemap(base_url, max_urls=max_urls)
    result["total_urls"] = len(urls)
    
    if not urls:
        return result
    
    # Process URLs in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for url in urls:
            future = executor.submit(
                _process_single_url,
                url,
                extract_content,
                extract_seo,
            )
            futures[future] = url
            time.sleep(delay)  # Rate limiting
        
        for future in as_completed(futures):
            url = futures[future]
            try:
                data = future.result()
                result["results"].append(data)
                result["processed"] += 1
            except Exception as exc:
                result["failed"] += 1
                result["results"].append({
                    "url": url,
                    "error": str(exc),
                })
    
    return result


def _process_single_url(
    url: str,
    extract_content: bool = True,
    extract_seo: bool = True,
) -> Dict[str, Any]:
    """Process a single URL and extract data."""
    result = {"url": url}
    
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text
        
        if extract_seo:
            seo_data = extract_all_structured_data(html, url)
            result["seo"] = seo_data
        
        if extract_content:
            content = smart_extract(html, url)
            result["title"] = content.get("title", "")
            result["content"] = content.get("content", "")
        
    except Exception as exc:
        result["error"] = str(exc)
    
    return result


# ---------------------------------------------------------------------------
# RSS/Atom Feed Parser
# ---------------------------------------------------------------------------

def parse_feed(feed_url: str, timeout: int = 15) -> Dict[str, Any]:
    """Parse an RSS or Atom feed.
    
    Returns:
        {
            "title": "Feed Title",
            "link": "https://example.com",
            "description": "...",
            "items": [
                {
                    "title": "Post Title",
                    "link": "https://example.com/post1",
                    "description": "...",
                    "published": "2024-01-01",
                    "author": "Author Name"
                }
            ]
        }
    """
    try:
        import feedparser
    except ImportError:
        return _parse_feed_manual(feed_url, timeout)
    
    try:
        feed = feedparser.parse(feed_url)
        
        result = {
            "title": feed.feed.get("title", ""),
            "link": feed.feed.get("link", ""),
            "description": feed.feed.get("description", ""),
            "language": feed.feed.get("language", ""),
            "updated": feed.feed.get("updated", ""),
            "items": [],
        }
        
        for entry in feed.entries:
            item = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "description": entry.get("summary", entry.get("description", "")),
                "published": entry.get("published", entry.get("updated", "")),
                "author": entry.get("author", ""),
            }
            
            # Get content if available
            if hasattr(entry, "content") and entry.content:
                item["content"] = entry.content[0].get("value", "")
            
            result["items"].append(item)
        
        return result
        
    except Exception as exc:
        logger.debug(f"Feed parsing failed: {exc}")
        return {}


def _parse_feed_manual(feed_url: str, timeout: int = 15) -> Dict[str, Any]:
    """Parse RSS/Atom feed without feedparser."""
    try:
        resp = httpx.get(
            feed_url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=timeout,
        )
        resp.raise_for_status()
        
        content = resp.text
        
        # Detect feed type
        is_atom = "<feed" in content.lower() and "atom" in content.lower()
        is_rss = "<rss" in content.lower() or "<channel" in content.lower()
        
        result = {
            "title": "",
            "link": "",
            "description": "",
            "items": [],
        }
        
        import re
        
        # Extract feed title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.DOTALL | re.IGNORECASE)
        if title_match:
            result["title"] = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
        
        # Extract items
        if is_atom:
            items = re.findall(r"<entry[^>]*>(.*?)</entry>", content, re.DOTALL | re.IGNORECASE)
            for item_xml in items[:20]:
                item = _parse_atom_entry(item_xml)
                result["items"].append(item)
        elif is_rss:
            items = re.findall(r"<item[^>]*>(.*?)</item>", content, re.DOTALL | re.IGNORECASE)
            for item_xml in items[:20]:
                item = _parse_rss_item(item_xml)
                result["items"].append(item)
        
        return result
        
    except Exception as exc:
        logger.debug(f"Manual feed parsing failed: {exc}")
        return {}


def _parse_rss_item(xml: str) -> Dict[str, str]:
    """Parse an RSS item."""
    import re
    
    title = re.search(r"<title[^>]*>(.*?)</title>", xml, re.DOTALL | re.IGNORECASE)
    link = re.search(r"<link[^>]*>(.*?)</link>", xml, re.DOTALL | re.IGNORECASE)
    desc = re.search(r"<description[^>]*>(.*?)</description>", xml, re.DOTALL | re.IGNORECASE)
    pub = re.search(r"<pubDate[^>]*>(.*?)</pubDate>", xml, re.DOTALL | re.IGNORECASE)
    author = re.search(r"<author[^>]*>(.*?)</author>", xml, re.DOTALL | re.IGNORECASE)
    
    return {
        "title": re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else "",
        "link": link.group(1).strip() if link else "",
        "description": re.sub(r"<[^>]+>", "", desc.group(1)).strip() if desc else "",
        "published": pub.group(1).strip() if pub else "",
        "author": re.sub(r"<[^>]+>", "", author.group(1)).strip() if author else "",
    }


def _parse_atom_entry(xml: str) -> Dict[str, str]:
    """Parse an Atom entry."""
    import re
    
    title = re.search(r"<title[^>]*>(.*?)</title>", xml, re.DOTALL | re.IGNORECASE)
    link = re.search(r'<link[^>]*href="([^"]*)"[^>]*/>', xml, re.IGNORECASE)
    summary = re.search(r"<summary[^>]*>(.*?)</summary>", xml, re.DOTALL | re.IGNORECASE)
    published = re.search(r"<published[^>]*>(.*?)</published>", xml, re.DOTALL | re.IGNORECASE)
    author = re.search(r"<name[^>]*>(.*?)</name>", xml, re.DOTALL | re.IGNORECASE)
    
    return {
        "title": re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else "",
        "link": link.group(1) if link else "",
        "description": re.sub(r"<[^>]+>", "", summary.group(1)).strip() if summary else "",
        "published": published.group(1).strip() if published else "",
        "author": re.sub(r"<[^>]+>", "", author.group(1)).strip() if author else "",
    }


def discover_feeds(base_url: str) -> List[str]:
    """Discover RSS/Atom feeds for a website."""
    feeds = set()
    
    # Common feed locations
    common_feeds = [
        "/feed",
        "/feed.xml",
        "/rss",
        "/rss.xml",
        "/atom.xml",
        "/feeds/posts/default",
        "/index.xml",
        "/blog/feed",
        "/blog/feed.xml",
        "/news/feed",
        "/feed.rss",
    ]
    
    parsed = urllib.parse.urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    
    for feed_path in common_feeds:
        try:
            url = base + feed_path
            resp = httpx.head(url, headers={"User-Agent": ua_rotator.get()}, timeout=10)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                if "xml" in content_type or "rss" in content_type or "atom" in content_type:
                    feeds.add(url)
        except Exception:
            continue
    
    return list(feeds)


# ---------------------------------------------------------------------------
# Wayback Machine CDX API
# ---------------------------------------------------------------------------

def wayback_cdx_search(
    url: str,
    from_date: str = None,
    to_date: str = None,
    limit: int = 100,
    match_type: str = "prefix",
) -> List[Dict[str, Any]]:
    """Search Wayback Machine CDX API for historical snapshots.
    
    Args:
        url: URL to search for
        from_date: Start date (YYYYMMDD)
        to_date: End date (YYYYMMDD)
        limit: Maximum results
        match_type: "prefix", "exact", "host", "domain"
    
    Returns:
        List of snapshot metadata
    """
    try:
        params = {
            "url": url,
            "output": "json",
            "limit": limit,
            "matchType": match_type,
            "fl": "timestamp,original,statuscode,digest,length",
        }
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        resp = httpx.get(
            "https://web.archive.org/cdx/search/cdx",
            params=params,
            headers={"User-Agent": ua_rotator.get()},
            timeout=30,
        )
        resp.raise_for_status()
        
        data = resp.json()
        
        if not data or len(data) < 2:
            return []
        
        # First row is header
        headers = data[0]
        results = []
        
        for row in data[1:]:
            entry = dict(zip(headers, row))
            entry["wayback_url"] = f"https://web.archive.org/web/{entry.get('timestamp', '')}/{entry.get('original', '')}"
            results.append(entry)
        
        return results
        
    except Exception as exc:
        logger.debug(f"Wayback CDX search failed: {exc}")
        return []


def wayback_latest_snapshot(url: str) -> Optional[Dict[str, str]]:
    """Get the latest Wayback Machine snapshot for a URL."""
    try:
        resp = httpx.get(
            "https://archive.org/wayback/available",
            params={"url": url},
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        snapshots = data.get("archived_snapshots", {})
        closest = snapshots.get("closest", {})
        
        if closest:
            return {
                "url": closest.get("url", ""),
                "timestamp": closest.get("timestamp", ""),
                "status": closest.get("status", ""),
            }
        
        return None
        
    except Exception as exc:
        logger.debug(f"Wayback latest snapshot failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Full Website Crawler
# ---------------------------------------------------------------------------

def _process_single_url(
    url: str,
    extract_content: bool = True,
    extract_seo: bool = True,
    respect_robots: bool = True,
    user_agent: str = "*",
) -> Dict[str, Any]:
    """Fetch and extract a single URL with robots + fetch guards.

    This is the worker used by ``crawl_website`` and ``collect_from_sitemap``.
    It enforces robots.txt (unless ``respect_robots=False``) and caps the
    response size / redirects so a single huge or looping page cannot exhaust
    the host.
    """
    if respect_robots:
        assert_allowed(url, user_agent)

    domain = _domain_key(url)
    sem = _domain_semaphore(domain)
    with sem:
        resp = guarded_get(url)
        resp.raise_for_status()
        body = resp.text[:_MAX_FETCH_BYTES]

    from agent_eye.document_intel import extract_document

    page: Dict[str, Any] = {"url": url}
    try:
        if extract_content:
            page["content"] = smart_extract(body, url, char_limit=15000)
        if extract_seo:
            page["seo"] = extract_all_structured_data(body, url)
    except Exception as exc:
        page["extract_error"] = str(exc)
    return page


def crawl_website(
    base_url: str,
    max_pages: int = 50,
    max_depth: int = 2,
    extract_content: bool = True,
    extract_seo: bool = True,
    follow_external: bool = False,
    url_filter: Callable[[str], bool] = None,
    respect_robots: bool = True,
    user_agent: str = "*",
) -> Dict[str, Any]:
    """Crawl a website starting from sitemaps and following links.

    Args:
        base_url: Starting URL
        max_pages: Maximum pages to crawl
        max_depth: Maximum link depth
        extract_content: Extract markdown content
        extract_seo: Extract SEO data
        follow_external: Follow external links
        url_filter: Custom URL filter function
        respect_robots: Skip URLs disallowed by robots.txt (default True)
        user_agent: User-agent string used for the robots.txt check

    
    Returns:
        Crawl results with all pages
    """
    result = {
        "base_url": base_url,
        "total_urls": 0,
        "crawled": 0,
        "failed": 0,
        "pages": [],
    }
    
    # Get URLs from sitemaps first
    urls = get_all_urls_from_sitemap(base_url, max_urls=max_pages)
    
    # Filter URLs if filter provided
    if url_filter:
        urls = [u for u in urls if url_filter(u)]
    
    result["total_urls"] = len(urls)
    
    # Process URLs
    for url in urls[:max_pages]:
        try:
            if respect_robots and not is_url_allowed(url, user_agent):
                result["skipped"] = result.get("skipped", 0) + 1
                result["pages"].append({
                    "url": url,
                    "skipped": True,
                    "reason": "robots.txt disallowed",
                })
                continue
            page_data = _process_single_url(
                url, extract_content, extract_seo, respect_robots, user_agent
            )
            result["pages"].append(page_data)
            result["crawled"] += 1
        except Exception as exc:
            result["failed"] += 1
            result["pages"].append({
                "url": url,
                "error": str(exc),
            })
    
    return result


# ---------------------------------------------------------------------------
# Batch Processor
# ---------------------------------------------------------------------------

def batch_process_urls(
    urls: List[str],
    extract_content: bool = True,
    extract_seo: bool = True,
    max_workers: int = 5,
    delay: float = 0.5,
) -> List[Dict[str, Any]]:
    """Process multiple URLs in parallel."""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for url in urls:
            future = executor.submit(
                _process_single_url,
                url,
                extract_content,
                extract_seo,
            )
            futures[future] = url
            time.sleep(delay)
        
        for future in as_completed(futures):
            url = futures[future]
            try:
                data = future.result()
                results.append(data)
            except Exception as exc:
                results.append({
                    "url": url,
                    "error": str(exc),
                })
    
    return results
