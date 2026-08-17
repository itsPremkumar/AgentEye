# -*- coding: utf-8 -*-
"""Agent Search Lite — Webhooks and scheduled searches.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

WEBHOOKS_FILE = Path.home() / ".agent-search" / "webhooks.json"
SCHEDULED_FILE = Path.home() / ".agent-search" / "scheduled.json"


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

def load_webhooks() -> List[Dict[str, Any]]:
    """Load webhook configurations."""
    if WEBHOOKS_FILE.exists():
        try:
            with open(WEBHOOKS_FILE, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.debug("Webhooks load failed: %s", exc)
    return []


def save_webhooks(webhooks: List[Dict[str, Any]]) -> None:
    """Save webhook configurations."""
    WEBHOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WEBHOOKS_FILE, "w") as f:
        json.dump(webhooks, f, indent=2)


def register_webhook(
    url: str,
    events: List[str] = None,
    secret: str = "",
) -> Dict[str, Any]:
    """Register a new webhook."""
    webhooks = load_webhooks()
    
    webhook = {
        "id": hashlib.md5(url.encode()).hexdigest()[:8],
        "url": url,
        "events": events or ["search.completed"],
        "secret": secret,
        "created_at": time.time(),
        "enabled": True,
    }
    
    webhooks.append(webhook)
    save_webhooks(webhooks)
    return webhook


def trigger_webhook(event: str, data: Dict[str, Any]) -> None:
    """Trigger webhooks for an event."""
    webhooks = load_webhooks()
    
    for webhook in webhooks:
        if not webhook.get("enabled"):
            continue
        if event not in webhook.get("events", []):
            continue
        
        try:
            payload = {
                "event": event,
                "timestamp": time.time(),
                "data": data,
            }
            
            resp = httpx.post(
                webhook["url"],
                json=payload,
                timeout=10,
            )
            logger.debug("Webhook %s triggered: %s", webhook["id"], resp.status_code)
        except Exception as exc:
            logger.debug("Webhook %s failed: %s", webhook["id"], exc)


# ---------------------------------------------------------------------------
# Scheduled Searches
# ---------------------------------------------------------------------------

def load_scheduled() -> List[Dict[str, Any]]:
    """Load scheduled searches."""
    if SCHEDULED_FILE.exists():
        try:
            with open(SCHEDULED_FILE, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.debug("Scheduled load failed: %s", exc)
    return []


def save_scheduled(scheduled: List[Dict[str, Any]]) -> None:
    """Save scheduled searches."""
    SCHEDULED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULED_FILE, "w") as f:
        json.dump(scheduled, f, indent=2)


def add_scheduled_search(
    query: str,
    interval_minutes: int,
    mode: str = "general",
    limit: int = 5,
) -> Dict[str, Any]:
    """Add a scheduled search."""
    scheduled = load_scheduled()
    
    entry = {
        "id": hashlib.md5(f"{query}:{interval_minutes}".encode()).hexdigest()[:8],
        "query": query,
        "mode": mode,
        "limit": limit,
        "interval_minutes": interval_minutes,
        "last_run": 0,
        "enabled": True,
        "created_at": time.time(),
    }
    
    scheduled.append(entry)
    save_scheduled(scheduled)
    return entry


def remove_scheduled_search(scheduled_id: str) -> bool:
    """Remove a scheduled search."""
    scheduled = load_scheduled()
    original_len = len(scheduled)
    scheduled = [s for s in scheduled if s["id"] != scheduled_id]
    
    if len(scheduled) < original_len:
        save_scheduled(scheduled)
        return True
    return False


def get_due_scheduled() -> List[Dict[str, Any]]:
    """Get scheduled searches that are due to run."""
    scheduled = load_scheduled()
    now = time.time()
    due = []
    
    for s in scheduled:
        if not s.get("enabled"):
            continue
        
        last_run = s.get("last_run", 0)
        interval = s.get("interval_minutes", 60) * 60
        
        if now - last_run >= interval:
            due.append(s)
    
    return due


def update_scheduled_run(scheduled_id: str) -> None:
    """Update last run time for a scheduled search."""
    scheduled = load_scheduled()
    
    for s in scheduled:
        if s["id"] == scheduled_id:
            s["last_run"] = time.time()
            break
    
    save_scheduled(scheduled)
