# -*- coding: utf-8 -*-
"""AgentLens — Multi-Level Cache.

L1: Memory (fastest, smallest)
L2: SQLite (persistent, medium)
L3: Filesystem (largest, slowest)

Copyright (c) 2026 AgentLens Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.expanduser("~/.agent-lens/cache")
DB_PATH = os.path.expanduser("~/.agent-lens/cache.db")


# ===========================================================================
# L1: Memory Cache (in-process, fastest)
# ===========================================================================

class MemoryCache:
    """Thread-safe in-memory cache."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_time: Dict[str, float] = {}
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                self.access_time[key] = time.time()
                return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        with self.lock:
            # Evict oldest if at capacity
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.access_time, key=self.access_time.get)
                del self.cache[oldest_key]
                del self.access_time[oldest_key]
            
            self.cache[key] = value
            self.access_time[key] = time.time()
    
    def has(self, key: str) -> bool:
        with self.lock:
            return key in self.cache
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.access_time.clear()
    
    @property
    def size(self) -> int:
        return len(self.cache)


# ===========================================================================
# L2: SQLite Cache (persistent, medium speed)
# ===========================================================================

class SQLiteCache:
    """Persistent SQLite cache with TTL."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    hits INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
            conn.commit()
    
    def get(self, key: str) -> Optional[Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?",
                    (key,)
                ).fetchone()
                
                if row:
                    value, expires_at = row
                    
                    # Check TTL
                    if expires_at and time.time() > expires_at:
                        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                        conn.commit()
                        return None
                    
                    # Update hit count
                    conn.execute(
                        "UPDATE cache SET hits = hits + 1 WHERE key = ?",
                        (key,)
                    )
                    conn.commit()
                    
                    return json.loads(value)
            
            return None
        except Exception as exc:
            logger.debug(f"SQLite cache get failed: {exc}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        try:
            expires_at = time.time() + ttl if ttl > 0 else None
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO cache (key, value, created_at, expires_at, hits)
                    VALUES (?, ?, ?, ?, 0)""",
                    (key, json.dumps(value, ensure_ascii=False), time.time(), expires_at)
                )
                conn.commit()
        except Exception as exc:
            logger.debug(f"SQLite cache set failed: {exc}")
    
    def has(self, key: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT 1 FROM cache WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)",
                    (key, time.time())
                ).fetchone()
                return row is not None
        except Exception:
            return False
    
    def cleanup(self, max_age: int = 86400):
        """Remove expired entries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM cache WHERE expires_at < ?",
                    (time.time(),)
                )
                conn.commit()
        except Exception as exc:
            logger.debug(f"Cache cleanup failed: {exc}")
    
    @property
    def size(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
                return row[0] if row else 0
        except Exception:
            return 0


# ===========================================================================
# L3: Filesystem Cache (largest, slowest)
# ===========================================================================

class FilesystemCache:
    """File-based cache for large data."""
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _key_to_path(self, key: str) -> str:
        """Convert cache key to file path."""
        hashed = hashlib.sha256(key.encode()).hexdigest()
        # Use first 2 chars as subdirectory for better performance
        return os.path.join(self.cache_dir, hashed[:2], hashed)
    
    def get(self, key: str, max_age: int = 86400) -> Optional[str]:
        path = self._key_to_path(key)
        
        try:
            if os.path.exists(path):
                # Check age
                age = time.time() - os.path.getmtime(path)
                if age <= max_age:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                else:
                    os.unlink(path)
        except Exception as exc:
            logger.debug(f"Filesystem cache get failed: {exc}")
        
        return None
    
    def set(self, key: str, content: str):
        path = self._key_to_path(key)
        
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as exc:
            logger.debug(f"Filesystem cache set failed: {exc}")
    
    def has(self, key: str) -> bool:
        return os.path.exists(self._key_to_path(key))
    
    def cleanup(self, max_age: int = 86400):
        """Remove old files."""
        try:
            now = time.time()
            for root, dirs, files in os.walk(self.cache_dir):
                for f in files:
                    path = os.path.join(root, f)
                    if now - os.path.getmtime(path) > max_age:
                        os.unlink(path)
        except Exception as exc:
            logger.debug(f"Filesystem cleanup failed: {exc}")


# ===========================================================================
# Multi-Level Cache Manager
# ===========================================================================

class MultiLevelCache:
    """L1 (memory) → L2 (SQLite) → L3 (filesystem) cache."""
    
    def __init__(self):
        self.l1 = MemoryCache(max_size=500)
        self.l2 = SQLiteCache()
        self.l3 = FilesystemCache()
    
    def get(self, key: str) -> Optional[Any]:
        """Get from cache (L1 → L2 → L3)."""
        # Try L1
        value = self.l1.get(key)
        if value is not None:
            return value
        
        # Try L2
        value = self.l2.get(key)
        if value is not None:
            # Promote to L1
            self.l1.set(key, value)
            return value
        
        # Try L3
        raw = self.l3.get(key)
        if raw is not None:
            try:
                value = json.loads(raw)
                # Promote to L2 and L1
                self.l2.set(key, value)
                self.l1.set(key, value)
                return value
            except json.JSONDecodeError:
                # Raw text content
                self.l2.set(key, raw)
                self.l1.set(key, raw)
                return raw
        
        return None
    
    def set(self, key: str, value: Any, l2_ttl: int = 3600):
        """Set in all cache levels."""
        self.l1.set(key, value)
        self.l2.set(key, value, l2_ttl)
        
        # Large content goes to L3
        try:
            raw = json.dumps(value, ensure_ascii=False)
            if len(raw) > 10000:  # >10KB
                self.l3.set(key, raw)
        except (TypeError, ValueError):
            pass
    
    def has(self, key: str) -> bool:
        return self.l1.has(key) or self.l2.has(key) or self.l3.has(key)
    
    def invalidate(self, key: str):
        """Remove from all levels."""
        # Remove from L1
        if key in self.l1.cache:
            del self.l1.cache[key]
            del self.l1.access_time[key]
        
        # Remove from L2
        try:
            with sqlite3.connect(self.l2.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
        except Exception:
            pass
        
        # Remove from L3
        path = self.l3._key_to_path(key)
        if os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass
    
    def clear(self):
        """Clear all cache levels."""
        self.l1.clear()
        try:
            with sqlite3.connect(self.l2.db_path) as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()
        except Exception:
            pass
        self.l3.cleanup(max_age=0)
    
    @property
    def stats(self) -> Dict[str, int]:
        return {
            "l1_size": self.l1.size,
            "l2_size": self.l2.size,
            "l3_size": sum(len(files) for _, _, files in os.walk(self.l3.cache_dir)),
        }


# ===========================================================================
# Global Cache Instance
# ===========================================================================

_cache = None

def get_cache() -> MultiLevelCache:
    """Get or create global cache instance."""
    global _cache
    if _cache is None:
        _cache = MultiLevelCache()
    return _cache


def cache_key(prefix: str, **kwargs) -> str:
    """Generate a deterministic cache key."""
    sorted_kwargs = sorted(kwargs.items())
    raw = f"{prefix}:{sorted_kwargs}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def cached(prefix: str, ttl: int = 3600):
    """Decorator for caching function results."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            cache = get_cache()
            key = cache_key(prefix, args=args, kwargs=kwargs)
            
            # Try cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Call function
            result = fn(*args, **kwargs)
            
            # Cache result
            if result is not None:
                cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator
