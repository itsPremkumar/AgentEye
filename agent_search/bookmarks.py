# -*- coding: utf-8 -*-
"""Agent Search Lite — Bookmarking and collections.

Save, tag, and organize search results.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BOOKMARKS_FILE = Path.home() / ".agent-search" / "bookmarks.json"
COLLECTIONS_FILE = Path.home() / ".agent-search" / "collections.json"


def load_bookmarks() -> List[Dict[str, Any]]:
    """Load saved bookmarks."""
    if BOOKMARKS_FILE.exists():
        try:
            with open(BOOKMARKS_FILE, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.debug("Bookmarks load failed: %s", exc)
    return []


def save_bookmarks(bookmarks: List[Dict[str, Any]]) -> None:
    """Save bookmarks to file."""
    BOOKMARKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOKMARKS_FILE, "w") as f:
        json.dump(bookmarks, f, indent=2)


def add_bookmark(
    url: str,
    title: str,
    description: str = "",
    tags: List[str] = None,
    source: str = "",
    query: str = "",
) -> Dict[str, Any]:
    """Add a bookmark."""
    bookmarks = load_bookmarks()
    
    # Check if already bookmarked
    for b in bookmarks:
        if b["url"] == url:
            return b
    
    bookmark = {
        "url": url,
        "title": title,
        "description": description,
        "tags": tags or [],
        "source": source,
        "query": query,
        "timestamp": time.time(),
    }
    
    bookmarks.insert(0, bookmark)
    save_bookmarks(bookmarks)
    return bookmark


def remove_bookmark(url: str) -> bool:
    """Remove a bookmark by URL."""
    bookmarks = load_bookmarks()
    original_len = len(bookmarks)
    bookmarks = [b for b in bookmarks if b["url"] != url]
    
    if len(bookmarks) < original_len:
        save_bookmarks(bookmarks)
        return True
    return False


def search_bookmarks(query: str = "", tags: List[str] = None) -> List[Dict[str, Any]]:
    """Search bookmarks by query or tags."""
    bookmarks = load_bookmarks()
    
    if not query and not tags:
        return bookmarks
    
    results = []
    for b in bookmarks:
        match = False
        
        if query:
            query_lower = query.lower()
            if (query_lower in b["title"].lower() or
                query_lower in b["description"].lower() or
                query_lower in b["url"].lower()):
                match = True
        
        if tags:
            if any(t in b.get("tags", []) for t in tags):
                match = True
        
        if match:
            results.append(b)
    
    return results


def load_collections() -> Dict[str, List[str]]:
    """Load search collections."""
    if COLLECTIONS_FILE.exists():
        try:
            with open(COLLECTIONS_FILE, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.debug("Collections load failed: %s", exc)
    return {}


def save_collections(collections: Dict[str, List[str]]) -> None:
    """Save collections to file."""
    COLLECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COLLECTIONS_FILE, "w") as f:
        json.dump(collections, f, indent=2)


def create_collection(name: str) -> bool:
    """Create a new collection."""
    collections = load_collections()
    if name in collections:
        return False
    collections[name] = []
    save_collections(collections)
    return True


def add_to_collection(name: str, url: str) -> bool:
    """Add URL to collection."""
    collections = load_collections()
    if name not in collections:
        return False
    if url not in collections[name]:
        collections[name].append(url)
        save_collections(collections)
    return True


def get_collection(name: str) -> Optional[List[str]]:
    """Get URLs in a collection."""
    collections = load_collections()
    return collections.get(name)
