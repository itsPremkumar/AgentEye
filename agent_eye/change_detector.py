# -*- coding: utf-8 -*-
"""AgentLens — Change Detection Engine.

Monitors websites for changes: price updates, content modifications, page availability.

Copyright (c) 2026 AgentLens Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

from agent_eye.throttle import ua_rotator

logger = logging.getLogger(__name__)

# Database for storing monitor state
DEFAULT_DB = os.path.expanduser("~/.agent-lens/changes.db")


# ---------------------------------------------------------------------------
# Change Monitor
# ---------------------------------------------------------------------------

class ChangeMonitor:
    """Monitor a URL for changes."""
    
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    selector TEXT,
                    last_hash TEXT,
                    last_content TEXT,
                    last_status INTEGER,
                    last_checked REAL,
                    change_count INTEGER DEFAULT 0,
                    created_at REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    monitor_id INTEGER,
                    url TEXT NOT NULL,
                    change_type TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    timestamp REAL,
                    FOREIGN KEY (monitor_id) REFERENCES monitors (id)
                )
            """)
            
            conn.commit()
    
    def add_monitor(self, url: str, selector: str = None) -> int:
        """Add a URL to monitor."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO monitors (url, selector, created_at) VALUES (?, ?, ?)",
                (url, selector, time.time())
            )
            conn.commit()
            return cursor.lastrowid
    
    def check(self, monitor_id: int) -> Optional[Dict[str, Any]]:
        """Check a monitor for changes."""
        with sqlite3.connect(self.db_path) as conn:
            monitor = conn.execute(
                "SELECT * FROM monitors WHERE id = ?",
                (monitor_id,)
            ).fetchone()
            
            if not monitor:
                return None
            
            url = monitor[1]
            selector = monitor[2]
            last_hash = monitor[3]
            
            # Fetch current content
            try:
                resp = httpx.get(
                    url,
                    headers={"User-Agent": ua_rotator.get()},
                    timeout=30,
                    follow_redirects=True,
                )
                resp.raise_for_status()
                current_content = resp.text
                current_status = resp.status_code
            except Exception as exc:
                # Page might be down
                change = {
                    "url": url,
                    "change_type": "error",
                    "old_value": f"status: {monitor[5]}",
                    "new_value": str(exc),
                    "timestamp": time.time(),
                }
                
                conn.execute(
                    "INSERT INTO changes (monitor_id, url, change_type, old_value, new_value, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (monitor_id, url, "error", change["old_value"], change["new_value"], time.time())
                )
                conn.execute(
                    "UPDATE monitors SET last_checked = ?, last_status = ? WHERE id = ?",
                    (time.time(), 0, monitor_id)
                )
                conn.commit()
                
                return change
            
            # Extract relevant content if selector provided
            if selector:
                current_content = _extract_with_selector(current_content, selector)
            
            # Hash the content
            current_hash = hashlib.sha256(current_content.encode()).hexdigest()
            
            # Compare
            if last_hash and current_hash != last_hash:
                # Change detected!
                change = {
                    "url": url,
                    "change_type": "content_changed",
                    "old_value": f"hash: {last_hash[:16]}...",
                    "new_value": f"hash: {current_hash[:16]}...",
                    "timestamp": time.time(),
                }
                
                conn.execute(
                    "INSERT INTO changes (monitor_id, url, change_type, old_value, new_value, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (monitor_id, url, "content_changed", change["old_value"], change["new_value"], time.time())
                )
                conn.execute(
                    "UPDATE monitors SET last_hash = ?, last_content = ?, last_status = ?, last_checked = ?, change_count = change_count + 1 WHERE id = ?",
                    (current_hash, current_content[:1000], current_status, time.time(), monitor_id)
                )
                conn.commit()
                
                return change
            
            # No previous hash, just store
            conn.execute(
                "UPDATE monitors SET last_hash = ?, last_content = ?, last_status = ?, last_checked = ? WHERE id = ?",
                (current_hash, current_content[:1000], current_status, time.time(), monitor_id)
            )
            conn.commit()
            
            return {
                "url": url,
                "change_type": "initial_check",
                "new_value": f"hash: {current_hash[:16]}...",
                "timestamp": time.time(),
            }
    
    def get_changes(self, monitor_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get change history for a monitor."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM changes WHERE monitor_id = ? ORDER BY timestamp DESC LIMIT ?",
                (monitor_id, limit)
            ).fetchall()
            
            return [
                {
                    "id": row[0],
                    "url": row[2],
                    "change_type": row[3],
                    "old_value": row[4],
                    "new_value": row[5],
                    "timestamp": row[6],
                }
                for row in rows
            ]
    
    def list_monitors(self) -> List[Dict[str, Any]]:
        """List all monitors."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM monitors").fetchall()
            
            return [
                {
                    "id": row[0],
                    "url": row[1],
                    "selector": row[2],
                    "last_hash": row[3],
                    "last_status": row[5],
                    "last_checked": row[6],
                    "change_count": row[7],
                }
                for row in rows
            ]


def _extract_with_selector(html: str, selector: str) -> str:
    """Extract content using a CSS selector."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select(selector)
        return "\n".join(str(el) for el in elements)
    except ImportError:
        return html


# ---------------------------------------------------------------------------
# Price Monitor
# ---------------------------------------------------------------------------

def monitor_price(url: str, selector: str = None) -> Dict[str, Any]:
    """Monitor a product page for price changes."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text
        
        # Try to extract price
        price = _extract_price(html, selector)
        
        return {
            "url": url,
            "price": price,
            "timestamp": time.time(),
        }
        
    except Exception as exc:
        return {
            "url": url,
            "error": str(exc),
            "timestamp": time.time(),
        }


def _extract_price(html: str, selector: str = None) -> Optional[str]:
    """Extract price from HTML."""
    # Common price patterns
    patterns = [
        r'[\$₹€£]\s*[\d,]+\.?\d*',
        r'price["\s:]+[\$₹€£]?\s*[\d,]+\.?\d*',
        r'["\']price["\']:\s*["\']?[\$₹€£]?\s*[\d,]+\.?\d*',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html)
        if matches:
            return matches[0]
    
    return None


# ---------------------------------------------------------------------------
# Content Monitor
# ---------------------------------------------------------------------------

def monitor_content(url: str, selector: str = None, interval: int = 300) -> Dict[str, Any]:
    """Monitor content changes on a page."""
    monitor = ChangeMonitor()
    
    # Add monitor
    monitor_id = monitor.add_monitor(url, selector)
    
    # Check for changes
    change = monitor.check(monitor_id)
    
    return {
        "monitor_id": monitor_id,
        "url": url,
        "change": change,
    }


# ---------------------------------------------------------------------------
# Availability Monitor
# ---------------------------------------------------------------------------

def check_availability(url: str) -> Dict[str, Any]:
    """Check if a website is available."""
    try:
        start = time.time()
        resp = httpx.get(
            url,
            headers={"User-Agent": ua_rotator.get()},
            timeout=15,
            follow_redirects=True,
        )
        elapsed = time.time() - start
        
        return {
            "url": url,
            "available": True,
            "status_code": resp.status_code,
            "response_time": elapsed,
            "timestamp": time.time(),
        }
        
    except Exception as exc:
        return {
            "url": url,
            "available": False,
            "error": str(exc),
            "timestamp": time.time(),
        }
