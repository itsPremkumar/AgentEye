# -*- coding: utf-8 -*-
"""Agent Search Lite — free web search + content extraction.

Completely free, zero API key required. Multiple backends with fallback:

Search backends (fallback chain):
    1. SearXNG (self-hosted meta-search)
    2. DDGS package (DuckDuckGo)
    3. Jina Reader + DuckDuckGo HTML
    4. GitHub CLI (code search)
    5. Hacker News API (tech news)
    6. Reddit JSON (discussions)

Extract backends:
    - Jina Reader (always free, zero-config)

No API keys required. Works out of the box.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Endpoints
_JINA_ENDPOINT = "https://r.jina.ai/"
_SEARXNG_DEFAULT = "http://localhost:8080"
_HACKERNEWS_API = "https://hacker-news.firebaseio.com/v0"
_REDDIT_BASE = "https://www.reddit.com"
_DDG_HTML = "https://html.duckduckgo.com/html/"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/1.0; +https://github.com/itsPremkumar/agent-search-lite)"
_MAX_JINA_BYTES = 5 * 1024 * 1024
_CACHE_TTL = 3600  # 1 hour


def _cache_dir() -> Path:
    """Get cache directory."""
    p = Path.home() / ".agent-search" / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_db() -> sqlite3.Connection:
    """Get SQLite cache connection."""
    db_path = _cache_dir() / "search_cache.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def _cache_get(key: str) -> Optional[str]:
    """Get cached value if not expired."""
    try:
        conn = _cache_db()
        row = conn.execute(
            "SELECT value, created_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        if row and (time.time() - row[1]) < _CACHE_TTL:
            return row[0]
    except Exception:
        pass
    return None


def _cache_set(key: str, value: str) -> None:
    """Set cache value."""
    try:
        conn = _cache_db()
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _resolve_ddg_url(url: str) -> str:
    """Resolve DuckDuckGo redirect URL to direct URL."""
    if "duckduckgo.com/l/" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in params:
                return urllib.parse.unquote(params["uddg"][0])
        except Exception:
            pass
    return url


async def _fetch_with_retry(
    url: str,
    method: str = "GET",
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> Optional[httpx.Response]:
    """Fetch URL with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                if method == "GET":
                    resp = await client.get(url, **kwargs)
                else:
                    resp = await client.post(url, **kwargs)
                if resp.status_code == 200:
                    return resp
                if resp.status_code == 429:  # Rate limited
                    delay = base_delay * (2 ** attempt)
                    logger.warning("Rate limited, retrying in %.1fs", delay)
                    await asyncio.sleep(delay)
                    continue
                if resp.status_code >= 500:  # Server error
                    delay = base_delay * (2 ** attempt)
                    logger.warning("Server error %d, retrying in %.1fs", resp.status_code, delay)
                    await asyncio.sleep(delay)
                    continue
                return resp
        except httpx.RequestError as exc:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning("Request failed: %s, retrying in %.1fs", exc, delay)
                await asyncio.sleep(delay)
            else:
                logger.error("Request failed after %d retries: %s", max_retries, exc)
    return None


def _searxng_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search via SearXNG (self-hosted meta-search engine)."""
    searxng_url = os.environ.get("SEARXNG_URL", _SEARXNG_DEFAULT)
    try:
        resp = httpx.get(
            f"{searxng_url}/search",
            params={"q": query, "format": "json", "pageno": 1},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])[:limit]
        web_results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("content", ""),
                "position": i + 1,
                "source": "searxng",
            }
            for i, r in enumerate(results)
        ]
        if web_results:
            return {"success": True, "data": {"web": web_results}}
    except Exception as exc:
        logger.debug("SearXNG search failed: %s", exc)
    return None


def _ddgs_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search via DDGS Python package (DuckDuckGo)."""
    try:
        from ddgs import DDGS
    except ImportError:
        return None
    try:
        results = []
        with DDGS(timeout=10) as client:
            for i, hit in enumerate(client.text(query, max_results=limit)):
                if i >= limit:
                    break
                url = str(hit.get("href") or hit.get("url") or "")
                results.append({
                    "title": str(hit.get("title", "")),
                    "url": url,
                    "description": str(hit.get("body", "")),
                    "position": i + 1,
                    "source": "ddgs",
                })
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        logger.debug("DDGS search failed: %s", exc)
    return None


def _jina_ddg_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search via Jina Reader + DuckDuckGo HTML (always free)."""
    try:
        ddg_url = f"{_DDG_HTML}?q={urllib.parse.quote(query)}"
        resp = httpx.get(
            f"{_JINA_ENDPOINT}{ddg_url}",
            headers={"User-Agent": _UA, "Accept": "text/plain"},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()
        text = resp.text[:20000]

        # Parse Jina Reader's markdown output
        results = []
        lines = text.split("\n")
        i = 0
        while i < len(lines) and len(results) < limit:
            line = lines[i].strip()
            match = re.match(r'^## \[(.+?)\]\((.+?)\)$', line)
            if match:
                title = match.group(1)
                url = _resolve_ddg_url(match.group(2))
                if "duckduckgo.com" in url and "/html/" in url:
                    i += 1
                    continue
                if title.startswith("Image"):
                    i += 1
                    continue
                snippet = ""
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith("[") and not next_line.startswith("!"):
                        snippet = next_line
                        break
                    j += 1
                results.append({
                    "title": title,
                    "url": url,
                    "description": snippet,
                    "position": len(results) + 1,
                    "source": "jina-ddg",
                })
            i += 1

        if results:
            return {"success": True, "data": {"web": results}}
        return {"success": False, "error": "Jina+DDG search returned no results"}

    except Exception as exc:
        logger.warning("Jina+DDG search failed: %s", exc)
        return {"success": False, "error": f"Jina+DDG search failed: {exc}"}


def _github_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search GitHub repos via gh CLI (free, no key)."""
    if not shutil.which("gh"):
        return None
    try:
        result = subprocess.run(
            ["gh", "search", "repos", query, "--sort", "stars",
             "--limit", str(limit), "--json", "fullName,description,url,stargazersCount"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        repos = json.loads(result.stdout) if result.stdout.strip() else []
        web_results = [
            {
                "title": r.get("fullName", ""),
                "url": r.get("url", ""),
                "description": r.get("description", f"⭐ {r.get('stargazersCount', 0)} stars"),
                "position": i + 1,
                "source": "github",
            }
            for i, r in enumerate(repos[:limit])
        ]
        if web_results:
            return {"success": True, "data": {"web": web_results}}
    except Exception as exc:
        logger.debug("GitHub search failed: %s", exc)
    return None


def _hackernews_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Hacker News via free API."""
    try:
        resp = httpx.get(
            f"{_HACKERNEWS_API}/search",
            params={"query": query, "tags": "story"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])[:limit]
        web_results = [
            {
                "title": h.get("title", ""),
                "url": h.get("url", f"https://news.ycombinator.com/item?id={h.get('objectID', '')}"),
                "description": f"⭐ {h.get('points', 0)} points | 💬 {h.get('num_comments', 0)} comments",
                "position": i + 1,
                "source": "hackernews",
            }
            for i, h in enumerate(hits)
        ]
        if web_results:
            return {"success": True, "data": {"web": web_results}}
    except Exception as exc:
        logger.debug("Hacker News search failed: %s", exc)
    return None


def _reddit_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Reddit via JSON API (no auth needed)."""
    try:
        resp = httpx.get(
            f"{_REDDIT_BASE}/search.json",
            params={"q": query, "limit": limit, "sort": "relevance"},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        posts = data.get("data", {}).get("children", [])[:limit]
        web_results = [
            {
                "title": p.get("data", {}).get("title", ""),
                "url": f"https://reddit.com{p.get('data', {}).get('permalink', '')}",
                "description": f"⭐ {p.get('data', {}).get('score', 0)} | 💬 {p.get('data', {}).get('num_comments', 0)} | r/{p.get('data', {}).get('subreddit', '')}",
                "position": i + 1,
                "source": "reddit",
            }
            for i, p in enumerate(posts)
        ]
        if web_results:
            return {"success": True, "data": {"web": web_results}}
    except Exception as exc:
        logger.debug("Reddit search failed: %s", exc)
    return None


def _jina_extract(urls: List[str], char_limit: int = 15000) -> List[Dict[str, Any]]:
    """Extract content from URLs via Jina Reader."""
    results = []
    for url in urls:
        try:
            if not url.startswith(("http://", "https://")):
                results.append({
                    "url": url, "title": "", "content": "",
                    "raw_content": "", "error": "Invalid URL",
                })
                continue

            resp = httpx.get(
                f"{_JINA_ENDPOINT}{url}",
                headers={"User-Agent": _UA, "Accept": "text/plain"},
                timeout=30,
                follow_redirects=True,
            )
            resp.raise_for_status()
            body = resp.text[:_MAX_JINA_BYTES]

            title = ""
            for line in body.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            if len(body) > char_limit:
                body = body[:char_limit] + "\n\n[TRUNCATED]"

            results.append({
                "url": url,
                "title": title,
                "content": body,
                "raw_content": body,
                "metadata": {"source": "jina-reader", "bytes": len(body)},
            })

        except httpx.HTTPStatusError as exc:
            results.append({
                "url": url, "title": "", "content": "", "raw_content": "",
                "error": f"HTTP {exc.response.status_code}",
            })
        except Exception as exc:
            results.append({
                "url": url, "title": "", "content": "", "raw_content": "",
                "error": str(exc),
            })
    return results


class AgentSearchLite:
    """Free web search + content extraction for AI agents.

    Completely free, zero API key required.
    """

    def __init__(self):
        self.search_backends = [
            ("searxng", _searxng_search),
            ("github", _github_search),
            ("hackernews", _hackernews_search),
            ("reddit", _reddit_search),
            ("ddgs", _ddgs_search),
            ("jina-ddg", lambda q, l: _jina_ddg_search(q, l)),
        ]

    def search(self, query: str, limit: int = 5, use_cache: bool = True, parallel: bool = True) -> Dict[str, Any]:
        """Search the web using multiple backends.

        Args:
            query: Search query
            limit: Max results per backend
            use_cache: Use SQLite cache
            parallel: Run backends in parallel and merge results

        Returns:
            {"success": True, "data": {"web": [...], "sources": {...}}} or {"success": False, "error": ...}
        """
        cache_key = f"search:{query}:{limit}"
        if use_cache:
            cached = _cache_get(cache_key)
            if cached:
                return json.loads(cached)

        all_results = []
        sources = {}

        if parallel:
            # Run backends in parallel for diverse results
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.search_backends)) as executor:
                futures = {}
                for name, backend in self.search_backends:
                    future = executor.submit(backend, query, limit)
                    futures[future] = name
                
                for future in concurrent.futures.as_completed(futures):
                    name = futures[future]
                    try:
                        result = future.result()
                        if result and result.get("success"):
                            web = result["data"]["web"]
                            all_results.extend(web)
                            sources[name] = len(web)
                    except Exception as exc:
                        logger.debug("Backend %s failed: %s", name, exc)
        else:
            # Fallback chain
            for name, backend in self.search_backends:
                try:
                    result = backend(query, limit)
                    if result and result.get("success"):
                        all_results.extend(result["data"]["web"])
                        sources[name] = len(result["data"]["web"])
                        break
                except Exception as exc:
                    logger.debug("Backend %s failed: %s", name, exc)

        if all_results:
            # Deduplicate by URL
            seen = set()
            unique = []
            for r in all_results:
                url = r.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    r["position"] = len(unique) + 1
                    unique.append(r)
            
            result = {
                "success": True,
                "data": {
                    "web": unique[:limit * 2],  # Return more results when parallel
                    "sources": sources,
                },
            }
            if use_cache:
                _cache_set(cache_key, json.dumps(result))
            return result

        return {"success": False, "error": "All search backends failed"}

    def extract(self, urls: List[str], char_limit: int = 15000) -> List[Dict[str, Any]]:
        """Extract content from URLs via Jina Reader.

        Args:
            urls: List of URLs to extract
            char_limit: Max chars per page

        Returns:
            List of result dicts with url, title, content, error
        """
        return _jina_extract(urls, char_limit)

    def doctor(self) -> Dict[str, Any]:
        """Check which backends are available."""
        backends = {}
        for name, _ in self.search_backends:
            if name == "searxng":
                try:
                    resp = httpx.get(f"{os.environ.get('SEARXNG_URL', _SEARXNG_DEFAULT)}/health", timeout=5)
                    backends[name] = "ok" if resp.status_code == 200 else "off"
                except Exception:
                    backends[name] = "off"
            elif name == "ddgs":
                try:
                    import ddgs
                    backends[name] = "ok"
                except ImportError:
                    backends[name] = "off"
            elif name == "github":
                backends[name] = "ok" if shutil.which("gh") else "off"
            else:
                backends[name] = "ok"
        return backends

    def doctor_report(self) -> str:
        """Get formatted health report."""
        status = self.doctor()
        lines = ["Agent Search Lite — Backend Status"]
        lines.append("=" * 45)
        for name, state in status.items():
            icon = "✅" if state == "ok" else "❌"
            lines.append(f"  {icon} {name}: {state}")
        return "\n".join(lines)
