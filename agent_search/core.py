# -*- coding: utf-8 -*-
"""Agent Search Lite — free web search + content extraction.

Completely free, zero API key required. Multiple backends with fallback.

Features:
- 10 Free Backends: DDGS, Jina+DDG, GitHub, HackerNews, arXiv, Wikipedia, Lemmy, StackOverflow, MDN, Dev.to
- Query expansion (multiple reformulations)
- Strategy modes (general, code, academic, news, community)
- Parallel backend execution with rate limiting
- SQLite caching
- Smart content extraction (SSR, JSON-LD, microdata)
- Result ranking (quality, verification, relevance, reliability)
- Pollution detection and filtering
- Token-conscious result formatting
- Site-specific search operators (site:github.com)
- Date filtering (after:YYYY-MM-DD, before:YYYY-MM-DD)
- User agent rotation (avoids blocking)
- Result clustering (groups similar results)
- Multi-language Wikipedia search
- Result freshness filtering
- Search history and analytics
- Export results (JSON, CSV, Markdown)
- MCP server mode
- Interactive REPL mode
- Configuration file support

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

import argparse
import concurrent.futures
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml

from agent_search.academic import arxiv_search, wikipedia_search
from agent_search.academic_backends import (
    crossref_search,
    openalex_search,
    pubmed_search,
    semantic_scholar_search,
)
from agent_search.bookmarks import (
    add_bookmark,
    add_to_collection,
    create_collection,
    get_collection,
    load_bookmarks,
    load_collections,
    remove_bookmark,
    search_bookmarks,
)
from agent_search.commerce_gov import (
    datagov_search,
    google_patents_search,
    jobs_search,
    nws_search,
    opencorporates_search,
    patents_search,
    undata_search,
    weather_search,
    worldbank_search,
)
from agent_search.config import add_to_history, ensure_config, get_analytics, load_history
from agent_search.dev_backends import (
    bitbucket_search,
    dockerhub_search,
    gitlab_search,
    npm_search,
    pypi_search,
)
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
from agent_search.export import export as export_results
from agent_search.extractors import smart_extract, score_readability
from agent_search.extra_backends import (
    cluster_results,
    devto_search,
    filter_by_freshness,
    get_suggestions,
    mdn_search,
    sort_by_freshness,
    wikipedia_search_multi,
)
from agent_search.knowledge_backends import (
    dbpedia_search,
    geonames_search,
    osm_search,
    rss_search,
    wayback_search,
    wikidata_search,
)
from agent_search.media_backends import (
    anilist_search,
    boardgameatlas_search,
    lastfm_search,
    mal_search,
    openlibrary_search,
    tmdb_search,
)
from agent_search.ranking import (
    cross_verify,
    format_token_conscious,
    is_polluted,
    quality_score,
    rank_results,
)
from agent_search.retry import retry_sync
from agent_search.search_engines import (
    bing_search,
    brave_search,
    duckduckgo_search,
    google_search,
    startpage_search,
)
from agent_search.scheduler import (
    add_scheduled_search,
    get_due_scheduled,
    load_scheduled,
    load_webhooks,
    register_webhook,
    remove_scheduled_search,
    trigger_webhook,
    update_scheduled_run,
)
from agent_search.social import lemmy_search, stackoverflow_search
from agent_search.social_backends import (
    mastodon_search,
    telegram_search,
    twitter_search,
    youtube_search,
)
from agent_search.more_backends import (
    crates_io_search,
    go_pkg_search,
    hacker_news_latest,
    lobsters_search,
    mojeek_search,
    packagist_search,
    pexels_search,
    pixabay_search,
    qwant_search,
    reddit_search,
    reddit_subreddit_posts,
    unsplash_search,
    yahoo_finance_quote,
    yahoo_finance_search,
)
from agent_search.summarize import summarize_results
from agent_search.templates import (
    TEMPLATES,
    apply_template,
    compare_results,
    get_template,
    get_template_names,
    search_content,
)
from agent_search.throttle import (
    RateLimiter,
    ReliabilityScorer,
    UserAgentRotator,
    rate_limiter,
    reliability_scorer,
    ua_rotator,
)

logger = logging.getLogger(__name__)

__version__ = "5.0.0"
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
_DDG_HTML = "https://html.duckduckgo.com/html/"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/3.1; +https://github.com/itsPremkumar/agent-search-lite)"
_MAX_JINA_BYTES = 5 * 1024 * 1024
_CACHE_TTL = 3600
_DEFAULT_TIMEOUT = 15.0

STRATEGY_MODES = {
    "general": {
        "backends": ["searxng", "ddgs", "jina-ddg", "hackernews", "github", "wikipedia", "stackoverflow", "lemmy", "mdn", "devto", "youtube", "twitter", "mastodon", "telegram", "osm", "wikidata", "geonames", "dbpedia", "rss", "wayback", "gitlab", "bitbucket", "npm", "pypi", "dockerhub", "pubmed", "semantic_scholar", "crossref", "openalex", "datagov", "worldbank", "undata", "weather", "nws", "patents", "google_patents", "jobs", "opencorporates", "tmdb", "lastfm", "openlibrary", "anilist", "mal", "boardgameatlas", "google", "bing", "brave", "duckduckgo", "startpage", "reddit", "yahoo_finance", "unsplash", "pexels", "pixabay", "crates_io", "packagist", "go_pkg", "lobsters", "mojeek", "qwant"],
        "description": "Broad web search across all sources",
    },
    "code": {
        "backends": ["github", "gitlab", "bitbucket", "stackoverflow", "npm", "pypi", "dockerhub", "crates_io", "packagist", "go_pkg", "searxng", "ddgs", "jina-ddg", "hackernews", "mdn", "devto"],
        "description": "Code repositories and programming resources",
        "query_suffixes": ["library", "framework", "package", "github"],
    },
    "academic": {
        "backends": ["arxiv", "pubmed", "semantic_scholar", "crossref", "openalex", "wikipedia", "ddgs", "jina-ddg", "github"],
        "description": "Academic papers and research",
        "query_suffixes": ["research paper", "arxiv", "study", "analysis"],
    },
    "news": {
        "backends": ["hackernews", "ddgs", "jina-ddg", "searxng", "wikipedia", "lemmy", "youtube", "twitter", "mastodon", "rss", "reddit", "lobsters"],
        "description": "Recent news and discussions",
        "query_suffixes": ["2026", "latest", "news", "announcement"],
    },
    "community": {
        "backends": ["lemmy", "hackernews", "stackoverflow", "wikipedia", "ddgs", "jina-ddg", "youtube", "twitter", "mastodon", "telegram", "reddit", "lobsters"],
        "description": "Community discussions and opinions",
        "query_suffixes": ["discussion", "opinion", "review", "experience"],
    },
}

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
        row = conn.execute("SELECT value, created_at FROM cache WHERE key = ?", (key,)).fetchone()
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
# Query Parsing
# ---------------------------------------------------------------------------

def parse_query(query: str) -> Dict[str, Any]:
    result = {"clean_query": query, "site": None, "date_after": None, "date_before": None, "lang": None}
    
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
    
    # Extract lang: operator
    lang_match = re.search(r'lang:(\S+)', query)
    if lang_match:
        result["lang"] = lang_match.group(1)
        result["clean_query"] = re.sub(r'lang:\S+', '', result["clean_query"]).strip()
    
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
    action_words = {"install", "setup", "configure", "build", "create", "deploy", "fix", "solve", "debug", "optimize", "improve", "migrate"}
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
    qualifiers = {"latest", "best", "top", "new", "recent", "current", "modern", "2024", "2025", "2026", "today", "now", "ultimate", "complete", "comprehensive", "definitive", "essential"}
    narrowed_words = [w for w in words if w not in qualifiers]
    if len(narrowed_words) < len(words) and len(narrowed_words) >= 2:
        return " ".join(narrowed_words)
    if not any(w in words for w in ["research", "study", "analysis", "paper", "academic"]):
        return f"{original} research analysis"
    return None


# ---------------------------------------------------------------------------
# Search Backends
# ---------------------------------------------------------------------------

@retry_sync(max_retries=2, base_delay=1.0)
def _searxng_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    searxng_url = os.environ.get("SEARXNG_URL", _SEARXNG_DEFAULT)
    try:
        resp = httpx.get(f"{searxng_url}/search", params={"q": query, "format": "json", "pageno": 1}, headers={"User-Agent": ua_rotator.get()}, timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])[:limit]
        web_results = [{"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("content", ""), "position": i + 1, "source": "searxng"} for i, r in enumerate(results)]
        if web_results:
            return {"success": True, "data": {"web": web_results}}
    except Exception as exc:
        logger.debug("SearXNG search failed: %s", exc)
    return None


@retry_sync(max_retries=2, base_delay=1.0)
def _ddgs_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
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
                results.append({"title": str(hit.get("title", "")), "url": url, "description": str(hit.get("body", "")), "position": i + 1, "source": "ddgs"})
        if results:
            return {"success": True, "data": {"web": results}}
    except Exception as exc:
        raise BackendError("ddgs", str(exc), original_error=exc)
    return None


@retry_sync(max_retries=2, base_delay=1.0)
def _jina_ddg_search(query: str, limit: int = 5) -> Dict[str, Any]:
    try:
        ddg_url = f"{_DDG_HTML}?q={urllib.parse.quote(query)}"
        resp = httpx.get(f"{_JINA_ENDPOINT}{ddg_url}", headers={"User-Agent": ua_rotator.get(), "Accept": "text/plain"}, timeout=30, follow_redirects=True)
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
                results.append({"title": title, "url": url, "description": snippet, "position": len(results) + 1, "source": "jina-ddg"})
            i += 1
        if results:
            return {"success": True, "data": {"web": results}}
        return {"success": False, "error": "Jina+DDG search returned no results"}
    except Exception as exc:
        raise BackendError("jina-ddg", str(exc), original_error=exc)


@retry_sync(max_retries=2, base_delay=1.0)
def _github_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    if not shutil.which("gh"):
        return None
    try:
        result = subprocess.run(["gh", "search", "repos", query, "--sort", "stars", "--limit", str(limit), "--json", "fullName,description,url,stargazersCount"], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        repos = json.loads(result.stdout) if result.stdout.strip() else []
        web_results = [{"title": r.get("fullName", ""), "url": r.get("url", ""), "description": r.get("description", f"⭐ {r.get('stargazersCount', 0)} stars"), "position": i + 1, "source": "github"} for i, r in enumerate(repos[:limit])]
        if web_results:
            return {"success": True, "data": {"web": web_results}}
    except Exception as exc:
        raise BackendError("github", str(exc), original_error=exc)
    return None


@retry_sync(max_retries=2, base_delay=1.0)
def _hackernews_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    try:
        resp = httpx.get(f"{_HACKERNEWS_API}/search", params={"query": query, "tags": "story", "hitsPerPage": limit}, headers={"User-Agent": ua_rotator.get()}, timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])[:limit]
        web_results = [{"title": h.get("title", ""), "url": h.get("url", f"https://news.ycombinator.com/item?id={h.get('objectID', '')}"), "description": f"⭐ {h.get('points', 0)} points | 💬 {h.get('num_comments', 0)} comments", "position": i + 1, "source": "hackernews"} for i, h in enumerate(hits)]
        if web_results:
            return {"success": True, "data": {"web": web_results}}
    except Exception as exc:
        raise BackendError("hackernews", str(exc), original_error=exc)
    return None


def _arxiv_search_wrapper(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    return arxiv_search(query, limit)


def _wikipedia_search_wrapper(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    return wikipedia_search(query, limit)


def _stackoverflow_search_wrapper(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    return stackoverflow_search(query, limit)


def _lemmy_search_wrapper(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    return lemmy_search(query, limit)


def _mdn_search_wrapper(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    return mdn_search(query, limit)


def _devto_search_wrapper(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    return devto_search(query, limit)


# ---------------------------------------------------------------------------
# Main Class
# ---------------------------------------------------------------------------

class AgentSearchLite:
    """Free web search + content extraction for AI agents."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or ensure_config()
        self.all_backends = {
            "searxng": _searxng_search,
            "ddgs": _ddgs_search,
            "jina-ddg": lambda q, l: _jina_ddg_search(q, l),
            "github": _github_search,
            "hackernews": _hackernews_search,
            "arxiv": _arxiv_search_wrapper,
            "wikipedia": _wikipedia_search_wrapper,
            "stackoverflow": _stackoverflow_search_wrapper,
            "lemmy": _lemmy_search_wrapper,
            "mdn": _mdn_search_wrapper,
            "devto": _devto_search_wrapper,
            "youtube": lambda q, l: youtube_search(q, l),
            "twitter": lambda q, l: twitter_search(q, l),
            "mastodon": lambda q, l: mastodon_search(q, l),
            "telegram": lambda q, l: telegram_search(q, l),
            "osm": lambda q, l: osm_search(q, l),
            "wikidata": lambda q, l: wikidata_search(q, l),
            "geonames": lambda q, l: geonames_search(q, l),
            "dbpedia": lambda q, l: dbpedia_search(q, l),
            "rss": lambda q, l: rss_search(q, l),
            "wayback": lambda q, l: wayback_search(q, l),
            "gitlab": lambda q, l: gitlab_search(q, l),
            "bitbucket": lambda q, l: bitbucket_search(q, l),
            "npm": lambda q, l: npm_search(q, l),
            "pypi": lambda q, l: pypi_search(q, l),
            "dockerhub": lambda q, l: dockerhub_search(q, l),
            "pubmed": lambda q, l: pubmed_search(q, l),
            "semantic_scholar": lambda q, l: semantic_scholar_search(q, l),
            "crossref": lambda q, l: crossref_search(q, l),
            "openalex": lambda q, l: openalex_search(q, l),
            "datagov": lambda q, l: datagov_search(q, l),
            "worldbank": lambda q, l: worldbank_search(q, l),
            "undata": lambda q, l: undata_search(q, l),
            "weather": lambda q, l: weather_search(q, l),
            "nws": lambda q, l: nws_search(q, l),
            "patents": lambda q, l: patents_search(q, l),
            "google_patents": lambda q, l: google_patents_search(q, l),
            "jobs": lambda q, l: jobs_search(q, l),
            "opencorporates": lambda q, l: opencorporates_search(q, l),
            "tmdb": lambda q, l: tmdb_search(q, l),
            "lastfm": lambda q, l: lastfm_search(q, l),
            "openlibrary": lambda q, l: openlibrary_search(q, l),
            "anilist": lambda q, l: anilist_search(q, l),
            "mal": lambda q, l: mal_search(q, l),
            "boardgameatlas": lambda q, l: boardgameatlas_search(q, l),
            "google": lambda q, l: google_search(q, l),
            "bing": lambda q, l: bing_search(q, l),
            "brave": lambda q, l: brave_search(q, l),
            "duckduckgo": lambda q, l: duckduckgo_search(q, l),
            "startpage": lambda q, l: startpage_search(q, l),
            "reddit": lambda q, l: reddit_search(q, l),
            "yahoo_finance": lambda q, l: yahoo_finance_search(q, l),
            "unsplash": lambda q, l: unsplash_search(q, l),
            "pexels": lambda q, l: pexels_search(q, l),
            "pixabay": lambda q, l: pixabay_search(q, l),
            "crates_io": lambda q, l: crates_io_search(q, l),
            "packagist": lambda q, l: packagist_search(q, l),
            "go_pkg": lambda q, l: go_pkg_search(q, l),
            "lobsters": lambda q, l: lobsters_search(q, l),
            "mojeek": lambda q, l: mojeek_search(q, l),
            "qwant": lambda q, l: qwant_search(q, l),
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
        lang: str = None,
        cluster: bool = False,
        fresh_days: int = None,
    ) -> Dict[str, Any]:
        """Search the web using multiple backends."""
        parsed = parse_query(query)
        clean_query = parsed["clean_query"]
        if site:
            parsed["site"] = site
        if date_after:
            parsed["date_after"] = date_after
        if date_before:
            parsed["date_before"] = date_before
        if lang:
            parsed["lang"] = lang
        
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

        cache_key = f"search:{query}:{limit}:{mode}:{parsed['site']}:{parsed['date_after']}:{parsed['date_before']}:{parsed['lang']}"
        if use_cache:
            cached = _cache_get(cache_key)
            if cached:
                return json.loads(cached)

        all_results = []
        sources = {}
        errors = {}
        backends = self._get_backends_for_mode(mode)

        # Apply rate limiting
        for name, backend in backends:
            rate_limiter.wait_if_needed(name)

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(backends) * len(queries), 10)) as executor:
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
            # Deduplicate
            seen = set()
            unique = []
            for r in all_results:
                url = r.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    r["position"] = len(unique) + 1
                    unique.append(r)
            
            # Cross-verify and rank
            unique = cross_verify(unique)
            unique = rank_results(unique, clean_query)
            unique = reliability_scorer.score_results(unique)
            
            # Filter polluted
            filtered = [r for r in unique if not is_polluted(r.get("title", ""), r.get("description", ""))]
            if filtered:
                unique = filtered
            
            # Freshness filter
            if fresh_days:
                unique = filter_by_freshness(unique, fresh_days)
            
            # Cluster if requested
            clusters = None
            if cluster:
                clusters = cluster_results(unique)
            
            result_data = {
                "web": unique[:limit * 3],
                "sources": sources,
                "queries": queries,
                "mode": mode,
                "errors": errors if errors else None,
                "parsed_query": parsed,
                "clusters": clusters,
            }
            
            if token_conscious:
                result_data["token_formatted"] = format_token_conscious(unique[:limit * 3], max_tokens)
            
            result = {"success": True, "data": result_data}
            if use_cache:
                _cache_set(cache_key, json.dumps(result))
            add_to_history(query, mode, len(unique), sources)
            return result
        
        return {"success": False, "error": "All search backends failed", "errors": errors}

    def extract(self, urls: List[str], char_limit: int = 15000, smart: bool = True) -> List[Dict[str, Any]]:
        """Extract content from URLs via Jina Reader."""
        results = []
        for url in urls:
            try:
                if not url.startswith(("http://", "https://")):
                    raise InvalidURLError(url)
                resp = httpx.get(f"{_JINA_ENDPOINT}{url}", headers={"User-Agent": ua_rotator.get(), "Accept": "text/plain"}, timeout=30, follow_redirects=True)
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
                    results.append({"url": url, "title": title, "content": content, "raw_content": body, "metadata": {"source": "jina-reader", "bytes": len(body)}})
            except InvalidURLError as exc:
                results.append({"url": url, "title": "", "content": "", "raw_content": "", "error": str(exc)})
            except httpx.HTTPStatusError as exc:
                results.append({"url": url, "title": "", "content": "", "raw_content": "", "error": f"HTTP {exc.response.status_code}"})
            except Exception as exc:
                results.append({"url": url, "title": "", "content": "", "raw_content": "", "error": str(exc)})
        return results

    def summarize(self, results: List[Dict[str, Any]], query: str = "", max_sentences: int = 3) -> str:
        return summarize_results(results, query, max_sentences)

    def export(self, results: List[Dict[str, Any]], format: str = "json", query: str = "") -> str:
        return export_results(results, format, query)

    def suggestions(self, query: str, limit: int = 5) -> List[str]:
        return get_suggestions(query, limit)

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
        lines.append("  lang:es — Search in Spanish Wikipedia")
        lines.append("")
        lines.append(f"Version: {__version__}")
        lines.append(f"License: {__license__}")
        return "\n".join(lines)

    def history(self) -> List[Dict[str, Any]]:
        return load_history()

    def analytics(self) -> Dict[str, Any]:
        return get_analytics()


# ---------------------------------------------------------------------------
# Interactive Mode
# ---------------------------------------------------------------------------

def interactive_mode():
    """Run interactive search REPL."""
    from agent_search.summarize import print_welcome, format_interactive_prompt
    search = AgentSearchLite()
    print_welcome()
    mode = "general"
    limit = 5
    last_results = []
    while True:
        try:
            prompt = format_interactive_prompt("", mode)
            query = input(prompt).strip()
            if not query:
                continue
            if query == "/quit":
                print("Goodbye!")
                break
            elif query == "/help":
                print_welcome()
                continue
            elif query.startswith("/mode "):
                mode = query.split()[1]
                print(f"Mode: {mode}")
                continue
            elif query.startswith("/limit "):
                limit = int(query.split()[1])
                print(f"Limit: {limit}")
                continue
            elif query.startswith("/export "):
                fmt = query.split()[1] if len(query.split()) > 1 else "json"
                print(search.export(last_results, fmt, "interactive"))
                continue
            elif query == "/history":
                for h in search.history()[:5]:
                    print(f"  {h['query'][:50]} ({h['result_count']} results)")
                continue
            elif query == "/doctor":
                print(search.doctor_report())
                continue
            else:
                result = search.search(query, limit=limit, mode=mode)
                if result["success"]:
                    last_results = result["data"]["web"]
                    for item in last_results[:limit]:
                        print(f"{item['position']}. {item['title']}")
                        print(f"   {item['url']}")
                        if item.get("description"):
                            print(f"   {item['description'][:100]}")
                        print()
                else:
                    print(f"Error: {result.get('error')}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as exc:
            print(f"Error: {exc}")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="agent-search-lite",
        description="Free web search + content extraction for AI agents",
        epilog="Agent Search Lite v3.1.0 — Based on Agent Reach by Panniantong (MIT)",
    )
    parser.add_argument("--version", action="version", version="agent-search-lite 4.0.0")
    
    sub = parser.add_subparsers(dest="command")
    
    # search
    p_search = sub.add_parser("search", help="Search the web")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-n", "--limit", type=int, default=5, help="Max results")
    p_search.add_argument("-m", "--mode", choices=list(STRATEGY_MODES.keys()), default="general", help="Strategy mode")
    p_search.add_argument("--no-cache", action="store_true", help="Skip cache")
    p_search.add_argument("--no-expand", action="store_true", help="Disable query expansion")
    p_search.add_argument("--json", action="store_true", help="Output JSON")
    p_search.add_argument("--token-conscious", action="store_true", help="Format results to minimize token usage")
    p_search.add_argument("--max-tokens", type=int, default=2000, help="Max tokens for token-conscious formatting")
    p_search.add_argument("--site", help="Search specific site (e.g., github.com, wikipedia.org)")
    p_search.add_argument("--after", help="Results after date (YYYY-MM-DD)")
    p_search.add_argument("--before", help="Results before date (YYYY-MM-DD)")
    p_search.add_argument("--lang", help="Language code (e.g., es, fr, zh)")
    p_search.add_argument("--cluster", action="store_true", help="Cluster similar results")
    p_search.add_argument("--fresh-days", type=int, help="Filter results newer than N days")
    p_search.add_argument("--summarize", action="store_true", help="Generate summary of results")
    p_search.add_argument("--export", choices=["json", "csv", "markdown"], help="Export format")
    p_search.add_argument("--output", help="Output file path")
    
    # extract
    p_extract = sub.add_parser("extract", help="Extract content from URLs")
    p_extract.add_argument("urls", nargs="+", help="URLs to extract")
    p_extract.add_argument("--char-limit", type=int, default=15000)
    p_extract.add_argument("--no-smart", action="store_true", help="Disable smart extraction")
    
    # doctor
    sub.add_parser("doctor", help="Check backend status")
    
    # modes
    sub.add_parser("modes", help="List available strategy modes")
    
    # history
    sub.add_parser("history", help="Show search history")
    
    # analytics
    sub.add_parser("analytics", help="Show search analytics")
    
    # suggestions
    p_suggest = sub.add_parser("suggest", help="Get search suggestions")
    p_suggest.add_argument("query", help="Partial query")
    p_suggest.add_argument("-n", "--limit", type=int, default=5, help="Number of suggestions")
    
    # interactive
    sub.add_parser("interactive", help="Start interactive search mode")
    sub.add_parser("repl", help="Alias for interactive mode")
    
    # bookmarks
    p_bookmark = sub.add_parser("bookmark", help="Bookmark a result")
    p_bookmark.add_argument("url", help="URL to bookmark")
    p_bookmark.add_argument("--title", help="Title for bookmark")
    p_bookmark.add_argument("--description", help="Description")
    p_bookmark.add_argument("--tags", help="Comma-separated tags")
    p_bookmark.add_argument("--query", help="Original search query")
    
    p_bookmarks = sub.add_parser("bookmarks", help="List/search bookmarks")
    p_bookmarks.add_argument("--query", help="Search bookmarks")
    p_bookmarks.add_argument("--tags", help="Filter by tags (comma-separated)")
    
    p_unbookmark = sub.add_parser("unbookmark", help="Remove a bookmark")
    p_unbookmark.add_argument("url", help="URL to remove")
    
    # collections
    p_collection = sub.add_parser("collection", help="Create a collection")
    p_collection.add_argument("name", help="Collection name")
    
    p_add_to_collection = sub.add_parser("add-to-collection", help="Add URL to collection")
    p_add_to_collection.add_argument("collection", help="Collection name")
    p_add_to_collection.add_argument("url", help="URL to add")
    
    p_collections = sub.add_parser("collections", help="List collections")
    p_collections.add_argument("--name", help="Show specific collection")
    
    # templates
    p_template = sub.add_parser("template", help="Apply a search template")
    p_template.add_argument("name", help="Template name")
    p_template.add_argument("--topic", required=True, help="Topic for template")
    p_template.add_argument("--topic2", help="Second topic (for comparison)")
    p_template.add_argument("--lang", help="Language (for code search)")
    
    sub.add_parser("templates", help="List available templates")
    
    # compare
    p_compare = sub.add_parser("compare", help="Compare two search queries")
    p_compare.add_argument("query1", help="First query")
    p_compare.add_argument("query2", help="Second query")
    p_compare.add_argument("-n", "--limit", type=int, default=5, help="Max results per query")
    
    # content search
    p_content = sub.add_parser("content", help="Search within extracted content")
    p_content.add_argument("url", help="URL to search within")
    p_content.add_argument("term", help="Search term")
    p_content.add_argument("--context", type=int, default=100, help="Context characters")
    
    # schedule
    p_schedule = sub.add_parser("schedule", help="Add scheduled search")
    p_schedule.add_argument("query", help="Search query")
    p_schedule.add_argument("interval", type=int, help="Interval in minutes")
    p_schedule.add_argument("-m", "--mode", default="general", help="Search mode")
    p_schedule.add_argument("-n", "--limit", type=int, default=5, help="Max results")
    
    p_scheduled = sub.add_parser("scheduled", help="List scheduled searches")
    
    p_remove_schedule = sub.add_parser("unschedule", help="Remove scheduled search")
    p_remove_schedule.add_argument("id", help="Scheduled search ID")
    
    # webhooks
    p_webhook = sub.add_parser("webhook", help="Register webhook")
    p_webhook.add_argument("url", help="Webhook URL")
    p_webhook.add_argument("--events", help="Comma-separated events")
    p_webhook.add_argument("--secret", help="Webhook secret")
    
    sub.add_parser("webhooks", help="List webhooks")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        search = AgentSearchLite()
        
        if args.command == "search":
            result = search.search(
                args.query,
                limit=args.limit,
                mode=args.mode,
                use_cache=not args.no_cache,
                expand=not args.no_expand,
                token_conscious=args.token_conscious,
                max_tokens=args.max_tokens,
                site=args.site,
                date_after=args.after,
                date_before=args.before,
                lang=args.lang,
                cluster=args.cluster,
                fresh_days=args.fresh_days,
            )
            if args.json or args.export:
                output = search.export(result.get("data", {}).get("web", []), args.export or "json", args.query)
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(output)
                    print(f"Results saved to {args.output}")
                else:
                    print(output)
            else:
                if result["success"]:
                    print(f"Mode: {result['data'].get('mode', 'general')}")
                    print(f"Queries: {result['data'].get('queries', [])}")
                    print(f"Sources: {result['data'].get('sources', {})}")
                    if result['data'].get('errors'):
                        print(f"Errors: {result['data']['errors']}")
                    print(f"Results: {len(result['data']['web'])}")
                    print()
                    for item in result["data"]["web"]:
                        print(f"{item['position']}. {item['title']}")
                        print(f"   {item['url']}")
                        if item.get("description"):
                            print(f"   {item['description'][:100]}")
                        print(f"   [source: {item.get('source', 'unknown')} | relevance: {item.get('relevance_score', 0):.2f} | reliability: {item.get('reliability_score', 0):.2f}]")
                        print()
                    if args.summarize:
                        print("=== Summary ===")
                        print(search.summarize(result["data"]["web"], args.query))
                else:
                    print(f"Error: {result.get('error')}", file=sys.stderr)
                    if result.get('errors'):
                        print("Details:", file=sys.stderr)
                        for backend, err in result['errors'].items():
                            print(f"  {backend}: {err}", file=sys.stderr)
                    sys.exit(1)
        
        elif args.command == "extract":
            results = search.extract(args.urls, char_limit=args.char_limit, smart=not args.no_smart)
            for r in results:
                print(f"URL: {r['url']}")
                print(f"Title: {r.get('title', '(none)')}")
                print(f"Content: {len(r.get('content', ''))} chars")
                if r.get("error"):
                    print(f"Error: {r['error']}")
                else:
                    print(r.get("content", "")[:500])
                print("---")
        
        elif args.command == "doctor":
            print(search.doctor_report())
        
        elif args.command == "modes":
            print("Available Strategy Modes:")
            print("=" * 45)
            for mode, config in STRATEGY_MODES.items():
                print(f"\n  {mode}:")
                print(f"    {config['description']}")
                print(f"    Backends: {', '.join(config['backends'])}")
        
        elif args.command == "history":
            history = search.history()
            print("Search History:")
            print("=" * 45)
            for h in history[:10]:
                print(f"  {h['query'][:50]} ({h['result_count']} results)")
        
        elif args.command == "analytics":
            analytics = search.analytics()
            print("Search Analytics:")
            print("=" * 45)
            print(f"  Total searches: {analytics.get('total_searches', 0)}")
            print(f"  Modes used: {analytics.get('modes_used', {})}")
            print(f"  Sources used: {analytics.get('sources_used', {})}")
        
        elif args.command == "suggest":
            suggestions = search.suggestions(args.query, args.limit)
            print("Search Suggestions:")
            print("=" * 45)
            for s in suggestions:
                print(f"  - {s}")
        
        elif args.command in ("interactive", "repl"):
            interactive_mode()
        
        elif args.command == "bookmark":
            tags = args.tags.split(",") if args.tags else []
            add_bookmark(
                url=args.url,
                title=args.title or "",
                description=args.description or "",
                tags=tags,
                query=args.query or "",
            )
            print(f"✅ Bookmarked: {args.url[:60]}")
        
        elif args.command == "bookmarks":
            tags = args.tags.split(",") if args.tags else None
            bookmarks = search_bookmarks(query=args.query or "", tags=tags)
            print("Bookmarks:")
            print("=" * 50)
            for b in bookmarks:
                print(f"  {b['title'][:50]}")
                print(f"    {b['url'][:60]}")
                if b.get("tags"):
                    print(f"    Tags: {', '.join(b['tags'])}")
                print()
        
        elif args.command == "unbookmark":
            if remove_bookmark(args.url):
                print(f"✅ Removed bookmark: {args.url[:60]}")
            else:
                print(f"❌ Bookmark not found: {args.url[:60]}")
        
        elif args.command == "collection":
            if create_collection(args.name):
                print(f"✅ Collection created: {args.name}")
            else:
                print(f"❌ Collection already exists: {args.name}")
        
        elif args.command == "add-to-collection":
            if add_to_collection(args.collection, args.url):
                print(f"✅ Added to collection: {args.collection}")
            else:
                print(f"❌ Collection not found: {args.collection}")
        
        elif args.command == "collections":
            collections = load_collections()
            if args.name:
                urls = get_collection(args.name)
                if urls:
                    print(f"Collection: {args.name}")
                    for url in urls:
                        print(f"  {url}")
                else:
                    print(f"Collection not found: {args.name}")
            else:
                print("Collections:")
                for name, urls in collections.items():
                    print(f"  {name} ({len(urls)} items)")
        
        elif args.command == "templates":
            print("Available Templates:")
            print("=" * 50)
            for name in get_template_names():
                t = get_template(name)
                print(f"  {name}: {t['description']}")
                print(f"    Query: {t['query']}")
                print()
        
        elif args.command == "template":
            kwargs = {"topic": args.topic}
            if args.topic2:
                kwargs["topic2"] = args.topic2
            if args.lang:
                kwargs["lang"] = args.lang
            params = apply_template(args.name, **kwargs)
            if params:
                print(f"Template: {args.name}")
                print(f"  Query: {params['query']}")
                print(f"  Mode: {params['mode']}")
                if params.get('site'):
                    print(f"  Site: {params['site']}")
                # Execute the search
                result = search.search(
                    params['query'],
                    limit=params.get('limit', 5),
                    mode=params['mode'],
                    site=params.get('site'),
                )
                if result['success']:
                    for item in result['data']['web'][:5]:
                        print(f"  [{item['source']}] {item['title'][:50]}")
            else:
                print(f"Template not found: {args.name}")
        
        elif args.command == "compare":
            result1 = search.search(args.query1, limit=args.limit)
            result2 = search.search(args.query2, limit=args.limit)
            
            comparison = compare_results(
                result1.get('data', {}).get('web', []),
                result2.get('data', {}).get('web', []),
            )
            
            print(f"Comparing: '{args.query1}' vs '{args.query2}'")
            print("=" * 50)
            print(f"Similarity: {comparison['similarity']:.2f}")
            print(f"Common URLs: {len(comparison['common_urls'])}")
            print(f"Only first: {len(comparison['only_first'])}")
            print(f"Only second: {len(comparison['only_second'])}")
            
            if comparison['common_urls']:
                print("\nCommon results:")
                for url in comparison['common_urls'][:5]:
                    print(f"  - {url}")
        
        elif args.command == "content":
            result = search.extract([args.url])
            if result and result[0].get('content'):
                matches = search_content(result[0]['content'], args.term, args.context)
                print(f"Found {len(matches)} matches in {args.url}")
                for m in matches:
                    print(f"\n  Position {m['position']}:")
                    print(f"  {m['snippet'][:200]}")
            else:
                print(f"Could not extract content from {args.url}")
        
        elif args.command == "schedule":
            entry = add_scheduled_search(
                query=args.query,
                interval_minutes=args.interval,
                mode=args.mode,
                limit=args.limit,
            )
            print(f"✅ Scheduled search added: {entry['id']}")
            print(f"  Query: {args.query}")
            print(f"  Interval: {args.interval} minutes")
        
        elif args.command == "scheduled":
            scheduled = load_scheduled()
            print("Scheduled Searches:")
            print("=" * 50)
            for s in scheduled:
                print(f"  ID: {s['id']}")
                print(f"    Query: {s['query']}")
                print(f"    Interval: {s['interval_minutes']} minutes")
                print(f"    Enabled: {s['enabled']}")
                print()
        
        elif args.command == "unschedule":
            if remove_scheduled_search(args.id):
                print(f"✅ Removed scheduled search: {args.id}")
            else:
                print(f"❌ Scheduled search not found: {args.id}")
        
        elif args.command == "webhook":
            events = args.events.split(",") if args.events else None
            webhook = register_webhook(args.url, events, args.secret or "")
            print(f"✅ Webhook registered: {webhook['id']}")
            print(f"  URL: {webhook['url']}")
            print(f"  Events: {webhook['events']}")
        
        elif args.command == "webhooks":
            webhooks = load_webhooks()
            print("Registered Webhooks:")
            print("=" * 50)
            for wh in webhooks:
                print(f"  ID: {wh['id']}")
                print(f"    URL: {wh['url']}")
                print(f"    Events: {wh['events']}")
                print(f"    Enabled: {wh['enabled']}")
                print()
    
    except InvalidModeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(f"Valid modes: {', '.join(exc.valid_modes)}", file=sys.stderr)
        sys.exit(1)
    except InvalidURLError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except AgentSearchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
