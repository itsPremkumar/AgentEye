# -*- coding: utf-8 -*-
"""AgentLens — FTS5 Full-Text Search.

Search within cached content and indexed pages.

Copyright (c) 2026 AgentLens Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.expanduser("~/.agent-lens/search_index.db")


# ===========================================================================
# Full-Text Search Index
# ===========================================================================

class SearchIndex:
    """FTS5-based full-text search over cached content."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Enable FTS5
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                    url,
                    title,
                    content,
                    source,
                    timestamp,
                    tokenize='porter unicode61'
                )
            """)
            
            # Table for metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS index_meta (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    source TEXT,
                    indexed_at REAL
                )
            """)
            
            conn.commit()
    
    def add(self, url: str, title: str, content: str, source: str = "", timestamp: float = None):
        """Add a document to the index."""
        import time
        
        if timestamp is None:
            timestamp = time.time()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Remove existing entry if any
                conn.execute("DELETE FROM search_index WHERE url = ?", (url,))
                
                # Insert new entry
                conn.execute(
                    """INSERT INTO search_index (url, title, content, source, timestamp)
                    VALUES (?, ?, ?, ?, ?)""",
                    (url, title, content[:100000], source, timestamp)  # Limit content size
                )
                
                # Update metadata
                conn.execute(
                    """INSERT OR REPLACE INTO index_meta (url, title, source, indexed_at)
                    VALUES (?, ?, ?, ?)""",
                    (url, title, source, timestamp)
                )
                
                conn.commit()
        except Exception as exc:
            logger.debug(f"Index add failed: {exc}")
    
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search the index."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Use FTS5 MATCH for full-text search
                rows = conn.execute(
                    """SELECT url, title, source, timestamp,
                    snippet(search_index, 2, '<b>', '</b>', '...', 10) as snippet,
                    rank
                    FROM search_index
                    WHERE search_index MATCH ?
                    ORDER BY rank
                    LIMIT ?""",
                    (query, limit)
                ).fetchall()
                
                return [
                    {
                        "url": row[0],
                        "title": row[1],
                        "source": row[2],
                        "timestamp": row[3],
                        "snippet": row[4],
                        "rank": row[5],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.debug(f"Index search failed: {exc}")
            return []
    
    def search_with_highlight(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search with highlighted snippets."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """SELECT url, title, source,
                    snippet(search_index, 2, '<<<', '>>>', '...', 15) as snippet,
                    bm25(search_index) as score
                    FROM search_index
                    WHERE search_index MATCH ?
                    ORDER BY score ASC
                    LIMIT ?""",
                    (query, limit)
                ).fetchall()
                
                return [
                    {
                        "url": row[0],
                        "title": row[1],
                        "source": row[2],
                        "snippet": row[3],
                        "score": row[4],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.debug(f"Index search failed: {exc}")
            return []
    
    def remove(self, url: str):
        """Remove a document from the index."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM search_index WHERE url = ?", (url,))
                conn.execute("DELETE FROM index_meta WHERE url = ?", (url,))
                conn.commit()
        except Exception as exc:
            logger.debug(f"Index remove failed: {exc}")
    
    def clear(self):
        """Clear the entire index."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM search_index")
                conn.execute("DELETE FROM index_meta")
                conn.commit()
        except Exception as exc:
            logger.debug(f"Index clear failed: {exc}")
    
    @property
    def size(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM search_index").fetchone()
                return row[0] if row else 0
        except Exception:
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM search_index").fetchone()
                total_docs = row[0] if row else 0
                
                row = conn.execute("SELECT COUNT(DISTINCT source) FROM search_index").fetchone()
                total_sources = row[0] if row else 0
                
                row = conn.execute(
                    "SELECT source, COUNT(*) as cnt FROM search_index GROUP BY source ORDER BY cnt DESC LIMIT 10"
                ).fetchall()
                top_sources = [{"source": r[0], "count": r[1]} for r in row]
                
                return {
                    "total_documents": total_docs,
                    "total_sources": total_sources,
                    "top_sources": top_sources,
                }
        except Exception as exc:
            logger.debug(f"Stats failed: {exc}")
            return {"total_documents": 0, "total_sources": 0, "top_sources": []}


# ===========================================================================
# Global Index Instance
# ===========================================================================

_index = None

def get_index() -> SearchIndex:
    """Get or create global search index."""
    global _index
    if _index is None:
        _index = SearchIndex()
    return _index


def index_page(url: str, title: str, content: str, source: str = ""):
    """Index a page for full-text search."""
    index = get_index()
    index.add(url, title, content, source)


def search_pages(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search indexed pages."""
    index = get_index()
    return index.search(query, limit)
