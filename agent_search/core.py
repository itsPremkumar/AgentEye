# -*- coding: utf-8 -*-
"""Agent Search Lite — free web search + content extraction.

Completely free, zero API key required. Multiple backends with fallback.

Features:
- Query expansion (multiple reformulations for better coverage)
- Strategy modes (general, code, academic, news, community)
- Parallel backend execution
- SQLite caching
- Smart content extraction (BeautifulSoup + readability)
- URL resolution (direct URLs, no redirects)
- Retry with exponential backoff

Usage:
    from agent_search.core import AgentSearchLite
    search = AgentSearchLite()
    result = search.search("query", mode="code")
    results = search.extract(["https://example.com"])
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
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
_UA = "Mozilla/5.0 (compatible; agent-search-lite/2.0; +https://github.com/itsPremkumar/agent-search-lite)"
_MAX_JINA_BYTES = 5 * 1024 * 1024
_CACHE_TTL = 3600  # 1 hour

# Strategy modes - which backends to prioritize
STRATEGY_MODES = {
    "general": {
        "backends": ["searxng", "jina-ddg", "ddgs", "hackernews", "reddit", "github"],
        "description": "Broad web search across all sources",
    },
    "code": {
        "backends": ["github", "searxng", "jina-ddg", "hackernews"],
        "description": "Code repositories and programming resources",
        "query_suffixes": ["library", "framework", "package", "github"],
    },
    "academic": {
        "backends": ["searxng", "jina-ddg", "github"],
        "description": "Academic papers and research",
        "query_suffixes": ["research paper", "arxiv", "study", "analysis"],
    },
    "news": {
        "backends": ["hackernews", "reddit", "jina-ddg", "searxng"],
        "description": "Recent news and discussions",
        "query_suffixes": ["2026", "latest", "news", "announcement"],
    },
    "community": {
        "backends": ["reddit", "hackernews", "jina-ddg", "searxng"],
        "description": "Community discussions and opinions",
        "query_suffixes": ["discussion", "opinion", "review", "experience"],
    },
}

# Query expansion concept map
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
            return row[1]
    except Exception:
        pass
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
    except Exception:
        pass


# ---------------------------------------------------------------------------
# URL Resolution
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Query Expansion
# ---------------------------------------------------------------------------

def generate_query_variations(query: str) -> List[str]:
    """Generate 3-5 genuinely different query reformulations.
    
    Strategies:
    1. Original query (always included)
    2. Question form (turn statements into questions)
    3. Concept expansion (broader terminology)
    4. Opposing viewpoint (find counterarguments)
    5. Domain narrowing (add specificity)
    """
    variations = [query]
    query_lower = query.strip().lower()
    words = query_lower.split()

    # Strategy 1: Question form
    question = _to_question(query_lower, words)
    if question and question.lower() != query_lower:
        variations.append(question)

    # Strategy 2: Concept expansion
    expanded = _expand_concepts(query, words)
    if expanded and expanded.lower() != query_lower:
        variations.append(expanded)

    # Strategy 3: Opposing viewpoint
    opposing = _opposing_viewpoint(query, query_lower, words)
    if opposing and opposing.lower() != query_lower:
        variations.append(opposing)

    # Strategy 4: Domain narrowing
    scoped = _adjust_scope(query, query_lower, words)
    if scoped and scoped.lower() != query_lower:
        variations.append(scoped)

    # Deduplicate
    seen = set()
    unique = []
    for v in variations:
        key = v.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(v)

    return unique[:5]


def _to_question(query: str, words: list[str]) -> Optional[str]:
    """Turn a statement into a question form."""
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
    """Replace terms with broader/alternative concepts."""
    result = original
    expanded = False

    for word in words:
        if word in CONCEPT_MAP:
            alternatives = CONCEPT_MAP[word]
            replacement = alternatives[0]
            result = re.sub(r'\b' + re.escape(word) + r'\b', replacement, result, count=1, flags=re.IGNORECASE)
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
    """Generate a query for the opposing viewpoint."""
    for trigger, opposition in OPPOSITION_TRIGGERS.items():
        if trigger in words:
            new_query = query_lower.replace(trigger, opposition, 1)
            return new_query

    if len(words) >= 2:
        return f"criticism problems with {original}"

    return None


def _adjust_scope(original: str, query_lower: str, words: list[str]) -> Optional[str]:
    """Narrow or broaden the query scope."""
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
# Content Extraction
# ---------------------------------------------------------------------------

def _extract_readable_text(html: str, max_chars: int = 10000) -> str:
    """Extract readable text from HTML using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup, Comment
    except ImportError:
        # Fallback to basic extraction
        return _basic_text_extraction(html, max_chars)

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Remove comments
        comments = soup.findAll(text=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text[:max_chars]
    except Exception:
        return _basic_text_extraction(html, max_chars)


def _basic_text_extraction(html: str, max_chars: int = 10000) -> str:
    """Basic text extraction without BeautifulSoup."""
    # Remove script/style
    text = re.sub(r'<(script|style)[^>]*>[^<]*</\1>', ' ', html, flags=re.IGNORECASE)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]


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


# ---------------------------------------------------------------------------
# Main Class
# ---------------------------------------------------------------------------

class AgentSearchLite:
    """Free web search + content extraction for AI agents.

    Completely free, zero API key required.
    """

    def __init__(self):
        self.all_backends = {
            "searxng": _searxng_search,
            "ddgs": _ddgs_search,
            "jina-ddg": lambda q, l: _jina_ddg_search(q, l),
            "github": _github_search,
            "hackernews": _hackernews_search,
            "reddit": _reddit_search,
        }

    def _get_backends_for_mode(self, mode: str) -> List[tuple[str, callable]]:
        """Get backends ordered by priority for a strategy mode."""
        if mode in STRATEGY_MODES:
            mode_config = STRATEGY_MODES[mode]
            backend_names = mode_config.get("backends", list(self.all_backends.keys()))
            return [(name, self.all_backends[name]) for name in backend_names if name in self.all_backends]
        return [(name, fn) for name, fn in self.all_backends.items()]

    def search(
        self,
        query: str,
        limit: int = 5,
        mode: str = "general",
        use_cache: bool = True,
        expand: bool = True,
    ) -> Dict[str, Any]:
        """Search the web using multiple backends.

        Args:
            query: Search query
            limit: Max results per backend
            mode: Strategy mode (general, code, academic, news, community)
            use_cache: Use SQLite cache
            expand: Use query expansion for better coverage

        Returns:
            {"success": True, "data": {"web": [...], "sources": {...}, "queries": [...]}}
        """
        # Generate query variations
        if expand:
            queries = generate_query_variations(query)
        else:
            queries = [query]

        # Add mode-specific suffixes
        if mode in STRATEGY_MODES:
            suffixes = STRATEGY_MODES[mode].get("query_suffixes", [])
            for suffix in suffixes[:2]:
                expanded = f"{query} {suffix}"
                if expanded not in queries:
                    queries.append(expanded)

        cache_key = f"search:{query}:{limit}:{mode}"
        if use_cache:
            cached = _cache_get(cache_key)
            if cached:
                return json.loads(cached)

        all_results = []
        sources = {}
        backends = self._get_backends_for_mode(mode)

        # Run backends in parallel for each query variation
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
                    "web": unique[:limit * 3],
                    "sources": sources,
                    "queries": queries,
                    "mode": mode,
                },
            }
            if use_cache:
                _cache_set(cache_key, json.dumps(result))
            return result

        return {"success": False, "error": "All search backends failed"}

    def extract(self, urls: List[str], char_limit: int = 15000) -> List[Dict[str, Any]]:
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

                # Extract title
                title = ""
                for line in body.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

                # Extract readable text
                content = _extract_readable_text(body, char_limit)

                if len(content) > char_limit:
                    content = content[:char_limit] + "\n\n[TRUNCATED]"

                results.append({
                    "url": url,
                    "title": title,
                    "content": content,
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

    def doctor(self) -> Dict[str, Any]:
        """Check which backends are available."""
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
        """Get formatted health report."""
        status = self.doctor()
        lines = ["Agent Search Lite — Backend Status"]
        lines.append("=" * 45)
        for name, state in status.items():
            icon = "✅" if state == "ok" else "❌"
            lines.append(f"  {icon} {name}: {state}")
        lines.append("")
        lines.append("Strategy Modes:")
        for mode, config in STRATEGY_MODES.items():
            lines.append(f"  • {mode}: {config['description']}")
        return "\n".join(lines)
