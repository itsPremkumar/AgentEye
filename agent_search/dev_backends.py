# -*- coding: utf-8 -*-
"""Agent Search Lite — Developer Backends.

GitLab, Bitbucket, npm, PyPI, Docker Hub.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_GITLAB_API = "https://gitlab.com/api/v4"
_BITBUCKET_API = "https://api.bitbucket.org/2.0"
_NPM_API = "https://registry.npmjs.org"
_PYPI_API = "https://pypi.org/pypi"
_DOCKERHUB_API = "https://hub.docker.com/v2"
_UA = "Mozilla/5.0 (compatible; agent-search-lite/4.0; +https://github.com/itsPremkumar/agent-search-lite)"


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------

def gitlab_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search GitLab for repositories.
    
    Free API, no key required for public repos.
    """
    try:
        resp = httpx.get(
            f"{_GITLAB_API}/projects",
            params={
                "search": query,
                "per_page": limit,
                "order_by": "stars",
                "sort": "desc",
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        if not data:
            return None
        
        results = []
        for i, project in enumerate(data[:limit]):
            results.append({
                "title": project.get("name_with_namespace", ""),
                "url": project.get("web_url", ""),
                "description": project.get("description", "")[:300],
                "stars": project.get("star_count", 0),
                "forks": project.get("forks_count", 0),
                "source": "gitlab",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("GitLab search failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# Bitbucket
# ---------------------------------------------------------------------------

def bitbucket_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Bitbucket for repositories.
    
    Free API, no key required for public repos.
    """
    try:
        resp = httpx.get(
            f"{_BITBUCKET_API}/repositories",
            params={
                "q": f"name~\"{query}\"",
                "pagelen": limit,
                "sort": "-stars",
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        values = data.get("values", [])
        if not values:
            return None
        
        results = []
        for i, repo in enumerate(values[:limit]):
            results.append({
                "title": repo.get("full_name", ""),
                "url": repo.get("links", {}).get("html", {}).get("href", ""),
                "description": repo.get("description", "")[:300],
                "language": repo.get("language", ""),
                "source": "bitbucket",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("Bitbucket search failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# npm
# ---------------------------------------------------------------------------

def npm_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search npm for JavaScript packages.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            f"{_NPM_API}/-/v1/search",
            params={
                "text": query,
                "size": limit,
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        objects = data.get("objects", [])
        if not objects:
            return None
        
        results = []
        for i, obj in enumerate(objects[:limit]):
            package = obj.get("package", {})
            results.append({
                "title": package.get("name", ""),
                "url": package.get("links", {}).get("npm", ""),
                "description": package.get("description", "")[:300],
                "version": package.get("version", ""),
                "author": package.get("author", {}).get("name", ""),
                "source": "npm",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("npm search failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# PyPI
# ---------------------------------------------------------------------------

def pypi_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search PyPI for Python packages.
    
    Uses the PyPI JSON API (free, no key required).
    """
    try:
        resp = httpx.get(
            f"{_PYPI_API}/{query}/json",
            headers={"User-Agent": _UA},
            timeout=15,
        )
        
        if resp.status_code == 404:
            # Try search endpoint
            resp = httpx.get(
                f"{_PYPI_PI}/search/",
                params={"q": query},
                headers={"User-Agent": _UA},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])[:limit]
        else:
            resp.raise_for_status()
            data = resp.json()
            info = data.get("info", {})
            results = [{
                "title": info.get("name", ""),
                "url": info.get("package_url", ""),
                "description": info.get("summary", "")[:300],
                "version": info.get("version", ""),
                "author": info.get("author", ""),
                "source": "pypi",
                "position": 1,
            }]
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("PyPI search failed: %s", exc)
    
    return None


# ---------------------------------------------------------------------------
# Docker Hub
# ---------------------------------------------------------------------------

def dockerhub_search(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search Docker Hub for container images.
    
    Free API, no key required.
    """
    try:
        resp = httpx.get(
            f"{_DOCKERHUB_API}/search/repositories",
            params={
                "query": query,
                "page_size": limit,
                "ordering": "desc",
            },
            headers={"User-Agent": _UA},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        
        results_list = data.get("results", [])
        if not results_list:
            return None
        
        results = []
        for i, image in enumerate(results_list[:limit]):
            results.append({
                "title": image.get("repo_name", ""),
                "url": f"https://hub.docker.com/r/{image.get('repo_name', '')}",
                "description": image.get("short_description", "")[:300],
                "stars": image.get("star_count", 0),
                "pulls": image.get("pull_count", 0),
                "source": "dockerhub",
                "position": len(results) + 1,
            })
        
        if results:
            return {"success": True, "data": {"web": results}}
            
    except Exception as exc:
        logger.debug("Docker Hub search failed: %s", exc)
    
    return None
