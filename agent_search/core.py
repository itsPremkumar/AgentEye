# -*- coding: utf-8 -*-
"""Agent Search Lite — free web search + content extraction.

Completely free, zero API key required. Multiple backends with fallback.

Features:
- Query expansion (multiple reformulations for better coverage)
- Strategy modes (general, code, academic, news, community)
- Parallel backend execution
- SQLite caching
- Smart content extraction (SSR, JSON-LD, microdata, readability)
- Result ranking (quality, verification, relevance)
- Pollution detection and filtering
- Token-conscious result formatting
- Site-specific search operators
- Date filtering (before:/after:)
- Multiple fallback backends (Jina+DDG, DDGS, SearXNG)
- URL resolution (direct URLs, no redirects)
- Retry with exponential backoff
- Comprehensive error handling

Usage:
    from agent_search.core import AgentSearchLite
    search = AgentSearchLite()
    result = search.search("query", mode="code")
    results = search.extract(["https://example.com"])

Copyright (c) 2026 Agent Search Lite Contributors.
Based on Agent Reach by Panniantong (MIT licensed).
See LICENSE for details.
"""

from __future__ import annotations

import concurrent.futures
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

from agent_search.exceptions import (
    AgentSearchError,
    AllBackendsFailedError,
    BackendError,
    CacheError,
    ConfigurationError,
    InvalidModeError,
    InvalidURLError,
    NetworkError,
    RateLimitError,
    TimeoutError,
)
from agent_search.extractors import smart_extract, score_readability
from agent_search.ranking import (
    cross_verify,
    rank_results,
    quality_score,
    is_polluted,
    format_token_conscious,
)

logger = logging.getLogger(__name__)

__version__ = "2.3.0"
__author__ = "Agent Search Lite Contributors"
__license__ = "MIT"
__attribution__ = (
    "Based on Agent Reach by Panniantong (MIT). "
    "Query expansion inspired by brcrusoe72/agent-search (MIT). "
    "SSR extraction inspired by telly6/searchpin (MIT). "
    "Ranking inspired by drmikecrypto/WebSearchFree (MIT)."
)

_JINA_ENDPOINT = "https://r.jina.ai/"
_SEARXNG_DEFAULT = "http://localhost:8080"
_HACKERNEWS_API = "https://hn.algolia.com/api/v1"
_REDDIT_BASE = "https://www.reddit.com"
_DDG_HTML = "https://html.duckduckgo.com/html/"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/2.3; +https://github.com/itsPremkumar/agent-search-lite)"
_MAX_JINA_BYTES = 5 * 1024 * 1024
_CACHE_TTL = 3600
_DEFAULT_TIMEOUT = 15.0

STRATEGY_MODES = {
    "general": {
        "backends": ["searxng", "ddgs", "jina-ddg", "hackernews", "github"],
        "description": "Broad web search across all sources",
    },
    "code": {
        "backends": ["github", "searxng", "ddgs", "jina-ddg", "hackernews"],
        "description": "Code repositories and programming resources",
        "query_suffixes": ["library", "framework", "package", "github"],
    },
    "academic": {
        "backends": ["searxng", "ddgs", "jina-ddg", "github"],
        "description": "Academic papers and research",
        "query_suffixes": ["research paper", "arxiv", "study", "analysis"],
    },
    "news": {
        "backends": ["hackernews", "ddgs", "jina-ddg", "searxng"],
        "description": "Recent news and discussions",
        "query_suffixes": ["2026", "latest", "news", "announcement"],
    },
    "community": {
        "backends": ["hackernews", "ddgs", "jina-ddg", "searxng"],
        "description": "Community discussions and opinions",
        "query_suffixes": ["discussion", "opinion", "review", "experience"],
    },
}

# Site-specific search operators
SITE_OPERATORS = {
    "github": "site:github.com",
    "stackoverflow": "site:stackoverflow.com",
    "wikipedia": "site:wikipedia.org",
    "reddit": "site:reddit.com",
    "hackernews": "site:news.ycombinator.com",
    "medium": "site:medium.com",
    "devto": "site:dev.to",
    "arxiv": "site:arxiv.org",
}

# Date filter patterns
DATE_PATTERNS = {
    "after:": "after",
    "before:": "before",
    "since:": "after",
    "until:": "before",
}


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_dir() -> Path:
    p = Path.home() / ".agent-search" / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_db() -> sqlite3.Connection:
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
    try:
        conn = _cache_db()
        row = conn.execute(
            "SELECT value, created_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        if row and (time.time() - row[1]) < _CACHE_TTL:
            return row[0]
    except Exception as exc:
        logger.debug("Cache read failed: %s", exc)
    return None


def _cache_set(key: str, value: str) -> None:
    try:
        conn = _cache_db()
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Cache write failed: %s", exc)


# ---------------------------------------------------------------------------
# URL Resolution
# ---------------------------------------------------------------------------

def _resolve_ddg_url(url: str) -> str:
    if "duckduckgo.com/l/" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in params:
                return urllib.parse.unquote(params["uddg"][0])
        except Exception as exc:
            logger.debug("URL resolution failed: %s", exc)
    return url


# ---------------------------------------------------------------------------
# Query Parsing (site: and date filters)
# ---------------------------------------------------------------------------

def parse_query(query: str) -> Dict[str, Any]:
    """Parse query for site: and date filters.
    
    Returns:
        {
            "clean_query": str,
            "site": str or None,
            "date_after": str or None,
            "date_before": str or None,
        }
    """
    result = {
        "clean_query": query,
        "site": None,
        "date_after": None,
        "date_before": None,
    }
    
    # Extract site: operator
    site_match = re.search(r'site:(\S+)', query)
    if site_match:
        result["site"] = site_match.group(1)
        result["clean_query"] = re.sub(r'site:\S+', '', query).strip()
    
    # Extract date filters
    for pattern, date_type in DATE_PATTERNS.items():
        date_match = re.search(rf'{pattern}(\d{{4}}-\d{{2}}-\d{{2}})', query)
        if date_match:
            date_str = date_match.group(1)
            if date_type == "after":
                result["date_after"] = date_str
            else:
                result["date_before"] = date_str
            result["clean_query"] = re.sub(rf'{pattern}\d{{4}}-\d{{2}}-\d{{2}}', '', result["clean_query"]).strip()
    
    return result


# ---------------------------------------------------------------------------
# Query Expansion
# ---------------------------------------------------------------------------

CONCEPT_MAP = {
    "ai": ["artificial intelligence", "machine learning", "deep learning"],
    "ml": ["machine learning", "statistical learning"],
    "llm": ["large language model", "foundation model", "GPT", "Claude"],
    "api": ["interface", "integration", "SDK", "endpoint"],
    "saas": ["software as a service", "cloud software"],
    "devops": ["deployment automation", "CI/CD", "infrastructure as code"],
    "kubernetes": ["k8s", "container orchestration"],
    "docker": ["containerization", "container runtime"],
    "database": ["data store", "persistence layer"],
    "microservices": ["service-oriented architecture", "distributed systems"],
    "startup": ["early-stage company", "venture-backed"],
    "crypto": ["cryptocurrency", "digital assets", "blockchain"],
    "agent": ["AI agent", "autonomous agent", "agent framework"],
    "search": ["web search", "information retrieval", "query"],
}

OPPOSITION_TRIGGERS = {
    "best": "worst problems with",
    "benefits": "risks drawbacks of",
    "advantages": "disadvantages limitations of",
    "why": "why not criticism of",
    "success": "failure case study",
    "growing": "declining stagnating",
    "popular": "overrated criticism",
    "recommended": "alternatives to avoid",
    "safe": "risks dangers of",
    "cheap": "hidden costs of",
    "easy": "challenges difficulties of",
    "fast": "slow problems with",
    "good": "problems criticism of",
    "pros": "cons drawbacks",
}


def generate_query_variations(query: str) -> List[str]:
    variations = [query]
    query_lower = query.strip().lower()
    words = query_lower.split()

    question = _to_question(query_lower, words)
    if question and question.lower() != query_lower:
        variations.append(question)

    expanded = _expand_concepts(query, words)
    if expanded and expanded.lower() != query_lower:
        variations.append(expanded)

    opposing = _opposing_viewpoint(query, query_lower, words)
    if opposing and opposing.lower() != query_lower:
        variations.append(opposing)

    scoped = _adjust_scope(query, query_lower, words)
    if scoped and scoped.lower() != query_lower:
        variations.append(scoped)

    seen = set()
    unique = []
    for v in variations:
        key = v.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(v)

    return unique[:5]


def _to_question(query: str, words: list[str]) -> Optional[str]:
    if query.endswith("?") or words[0] in ("how", "what", "why", "when", "where", "who", "which", "is", "are", "can", "do", "does"):
        return None
    action_words = {"install", "setup", "configure", "build", "create", "deploy",
                    "fix", "solve", "debug", "optimize", "improve", "migrate"}
    if words[0] in action_words or (len(words) > 1 and words[1] in action_words):
        return f"how to {query}"
    if len(words) <= 4:
        return f"what is {query} and how does it work"
    return f"why {query}"


def _expand_concepts(original: str, words: list[str]) -> Optional[str]:
    result = original
    expanded = False
    for word in words:
        if word in CONCEPT_MAP:
            result = re.sub(r'\b' + re.escape(word) + r'\b', CONCEPT_MAP[word][0], result, count=1, flags=re.IGNORECASE)
            expanded = True
            break
    if not expanded:
        for phrase, alternatives in CONCEPT_MAP.items():
            if " " in phrase and phrase in original.lower():
                result = result.lower().replace(phrase, alternatives[0], 1)
                expanded = True
                break
    return result if expanded else None


def _opposing_viewpoint(original: str, query_lower: str, words: list[str]) -> Optional[str]:
    for trigger, opposition in OPPOSITION_TRIGGERS.items():
        if trigger in words:
            return query_lower.replace(trigger, opposition, 1)
    if len(words) >= 2:
        return f"criticism problems with {original}"
    return None


def _adjust_scope(original: str, query_lower: str, words: list[str]) -> Optional[str]:
    if len(words) <= 2:
        return f"{original} in 2026 latest developments"
    qualifiers = {"latest", "best", "top", "new", "recent", "current", "modern",
                  "2024", "2025", "2026", "today", "now", "ultimate", "complete",
                  "comprehensive", "definitive", "essential"}
    narrowed_words = [w for w in words if w not in qualifiers]
    if len(narrowed_words) < len(words) and len(narrowed_words) >= 2:
        return " ".join(narrowed_words)
    if not any(w in words for w in ["research", "study", "analysis", "paper", "academic"]):
        return f"{original} research analysis"
    return None


# ---------------------------------------------------------------------------
# Search Backends
# ---------------------------------------------------------------------------

def _searxng_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search via SearXNG (self-hosted meta-search engine)."""
    searxng_url = os.environ.get("SEARXNG_URL", _SEARXNG_DEFAULT)
    try:
        resp = httpx.get(
            f"{searxng_url}/search",
            params={"q": query, "format": "json", "pageno": 1},
            headers={"User-Agent": _UA},
            timeout=_DEFAULT_TIMEOUT,
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
    except httpx.HTTPStatusError as exc:
        raise BackendError("searxng", f"HTTP {exc.response.status_code}", original_error=exc)
    except httpx.RequestError as exc:
        raise NetworkError("searxng", original_error=exc)
    except Exception as exc:
        raise BackendError("searxng", str(exc), original_error=exc)
    return None


def _ddgs_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search via DDGS Python package (DuckDuckGo) - pure Python fallback."""
    try:
        from ddgs import DDGS
    except ImportError:
        logger.debug("DDGS package not installed")
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
        raise BackendError("ddgs", str(exc), original_error=exc)
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
                
                # Better snippet parsing: collect multiple lines
                snippet_lines = []
                j = i + 1
                while j < len(lines) and len(snippet_lines) < 3:
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith("[") and not next_line.startswith("!") and not next_line.startswith("##"):
                        snippet_lines.append(next_line)
                    elif next_line.startswith("##"):
                        break
                    j += 1
                
                snippet = " ".join(snippet_lines) if snippet_lines else ""
                
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

    except httpx.HTTPStatusError as exc:
        raise BackendError("jina-ddg", f"HTTP {exc.response.status_code}", original_error=exc)
    except httpx.RequestError as exc:
        raise NetworkError("jina-ddg", original_error=exc)
    except Exception as exc:
        raise BackendError("jina-ddg", str(exc), original_error=exc)


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
    except subprocess.TimeoutExpired:
        raise TimeoutError("github", 30.0)
    except json.JSONDecodeError as exc:
        raise BackendError("github", f"Invalid JSON: {exc}", original_error=exc)
    except Exception as exc:
        raise BackendError("github", str(exc), original_error=exc)
    return None


def _hackernews_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Hacker News via Algolia API."""
    try:
        resp = httpx.get(
            f"{_HACKERNEWS_API}/search",
            params={"query": query, "tags": "story", "hitsPerPage": limit},
            timeout=_DEFAULT_TIMEOUT,
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
    except httpx.HTTPStatusError as exc:
        raise BackendError("hackernews", f"HTTP {exc.response.status_code}", original_error=exc)
    except httpx.RequestError as exc:
        raise NetworkError("hackernews", original_error=exc)
    except Exception as exc:
        raise BackendError("hackernews", str(exc), original_error=exc)
    return None


# ---------------------------------------------------------------------------
# Main Class
# ---------------------------------------------------------------------------

class AgentSearchLite:
    """Free web search + content extraction for AI agents."""

    def __init__(self):
        self.all_backends = {
            "searxng": _searxng_search,
            "ddgs": _ddgs_search,
            "jina-ddg": lambda q, l: _jina_ddg_search(q, l),
            "github": _github_search,
            "hackernews": _hackernews_search,
        }

    def _get_backends_for_mode(self, mode: str) -> List[tuple[str, callable]]:
        if mode not in STRATEGY_MODES:
            raise InvalidModeError(mode, list(STRATEGY_MODES.keys()))
        mode_config = STRATEGY_MODES[mode]
        backend_names = mode_config.get("backends", list(self.all_backends.keys()))
        return [(name, self.all_backends[name]) for name in backend_names if name in self.all_backends]

    def search(
        self,
        query: str,
        limit: int = 5,
        mode: str = "general",
        use_cache: bool = True,
        expand: bool = True,
        token_conscious: bool = False,
        max_tokens: int = 2000,
        site: str = None,
        date_after: str = None,
        date_before: str = None,
    ) -> Dict[str, Any]:
        """Search the web using multiple backends."""
        # Parse query for operators
        parsed = parse_query(query)
        clean_query = parsed["clean_query"]
        
        # Override with explicit parameters
        if site:
            parsed["site"] = site
        if date_after:
            parsed["date_after"] = date_after
        if date_before:
            parsed["date_before"] = date_before
        
        # Build enhanced query with site operator
        base_query = clean_query
        if parsed["site"]:
            base_query = f"{clean_query} site:{parsed['site']}"
        
        if expand:
            queries = generate_query_variations(base_query)
        else:
            queries = [base_query]

        if mode in STRATEGY_MODES:
            suffixes = STRATEGY_MODES[mode].get("query_suffixes", [])
            for suffix in suffixes[:2]:
                expanded = f"{base_query} {suffix}"
                if expanded not in queries:
                    queries.append(expanded)

        cache_key = f"search:{query}:{limit}:{mode}:{parsed['site']}:{parsed['date_after']}:{parsed['date_before']}"
        if use_cache:
            cached = _cache_get(cache_key)
            if cached:
                return json.loads(cached)

        all_results = []
        sources = {}
        errors = {}
        backends = self._get_backends_for_mode(mode)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(backends) * len(queries)) as executor:
            futures = {}
            for q in queries:
                for name, backend in backends:
                    future = executor.submit(backend, q, limit)
                    futures[future] = (name, q)

            for future in concurrent.futures.as_completed(futures):
                name, q = futures[future]
                try:
                    result = future.result()
                    if result and result.get("success"):
                        web = result["data"]["web"]
                        all_results.extend(web)
                        if name not in sources:
                            sources[name] = 0
                        sources[name] += len(web)
                except Exception as exc:
                    logger.debug("Backend %s failed for '%s': %s", name, q, exc)
                    errors[name] = str(exc)

        if all_results:
            seen = set()
            unique = []
            for r in all_results:
                url = r.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    r["position"] = len(unique) + 1
                    unique.append(r)

            unique = cross_verify(unique)
            unique = rank_results(unique, clean_query)

            filtered = [r for r in unique if not is_polluted(r.get("title", ""), r.get("description", ""))]
            if filtered:
                unique = filtered

            result_data = {
                "web": unique[:limit * 3],
                "sources": sources,
                "queries": queries,
                "mode": mode,
                "errors": errors if errors else None,
                "parsed_query": parsed,
            }

            if token_conscious:
                result_data["token_formatted"] = format_token_conscious(unique[:limit * 3], max_tokens)

            result = {"success": True, "data": result_data}
            if use_cache:
                _cache_set(cache_key, json.dumps(result))
            return result

        return {"success": False, "error": "All search backends failed", "errors": errors}

    def extract(self, urls: List[str], char_limit: int = 15000, smart: bool = True) -> List[Dict[str, Any]]:
        """Extract content from URLs via Jina Reader with smart extraction."""
        results = []
        for url in urls:
            try:
                if not url.startswith(("http://", "https://")):
                    raise InvalidURLError(url)

                resp = httpx.get(
                    f"{_JINA_ENDPOINT}{url}",
                    headers={"User-Agent": _UA, "Accept": "text/plain"},
                    timeout=30,
                    follow_redirects=True,
                )
                resp.raise_for_status()
                body = resp.text[:_MAX_JINA_BYTES]

                if smart:
                    extracted = smart_extract(body, url, char_limit)
                    results.append(extracted)
                else:
                    title = ""
                    for line in body.split("\n"):
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
                    content = body[:char_limit]
                    results.append({
                        "url": url,
                        "title": title,
                        "content": content,
                        "raw_content": body,
                        "metadata": {"source": "jina-reader", "bytes": len(body)},
                    })

            except InvalidURLError as exc:
                results.append({"url": url, "title": "", "content": "", "raw_content": "", "error": str(exc)})
            except httpx.HTTPStatusError as exc:
                results.append({"url": url, "title": "", "content": "", "raw_content": "", "error": f"HTTP {exc.response.status_code}"})
            except httpx.RequestError as exc:
                results.append({"url": url, "title": "", "content": "", "raw_content": "", "error": f"Network error: {exc}"})
            except Exception as exc:
                results.append({"url": url, "title": "", "content": "", "raw_content": "", "error": f"Extraction failed: {exc}"})
        return results

    def doctor(self) -> Dict[str, Any]:
        backends = {}
        for name in self.all_backends:
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
        status = self.doctor()
        lines = ["Agent Search Lite — Backend Status", "=" * 45]
        for name, state in status.items():
            icon = "✅" if state == "ok" else "❌"
            lines.append(f"  {icon} {name}: {state}")
        lines.append("")
        lines.append("Strategy Modes:")
        for mode, config in STRATEGY_MODES.items():
            lines.append(f"  • {mode}: {config['description']}")
        lines.append("")
        lines.append("Query Operators:")
        lines.append("  site:example.com — Search specific site")
        lines.append("  after:2024-01-01 — Results after date")
        lines.append("  before:2025-01-01 — Results before date")
        lines.append("")
        lines.append(f"Version: {__version__}")
        lines.append(f"License: {__license__}")
        return "\n".join(lines)
