# -*- coding: utf-8 -*-
"""Agent Search Lite — Configuration and search history.

Manages user preferences and tracks past searches.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".agent-search"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
HISTORY_FILE = CONFIG_DIR / "history.json"
MAX_HISTORY = 100


def load_config() -> Dict[str, Any]:
    """Load configuration from ~/.agent-search/config.yaml."""
    import yaml
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = yaml.safe_load(f)
                if config:
                    return config
        except Exception as exc:
            logger.debug("Config load failed: %s", exc)
    
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to ~/.agent-search/config.yaml."""
    import yaml
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    logger.info("Config saved to %s", CONFIG_FILE)


def get_default_config() -> Dict[str, Any]:
    """Get default configuration."""
    return {
        "agent-search": {
            "version": "3.0.0",
            "defaults": {
                "limit": 5,
                "mode": "general",
                "use_cache": True,
                "expand": True,
                "token_conscious": False,
                "max_tokens": 2000,
            },
            "backends": {
                "searxng_url": "http://localhost:8080",
                "preferred_backend": None,
            },
            "proxy": {
                "http": os.environ.get("HTTP_PROXY", ""),
                "https": os.environ.get("HTTPS_PROXY", ""),
            },
            "export": {
                "default_format": "json",
                "include_raw": False,
            },
        }
    }


def ensure_config() -> Dict[str, Any]:
    """Ensure config file exists, create default if not."""
    if not CONFIG_FILE.exists():
        config = get_default_config()
        save_config(config)
        return config
    return load_config()


def add_to_history(query: str, mode: str, result_count: int, sources: Dict[str, int]) -> None:
    """Add a search to history."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    history = load_history()
    
    entry = {
        "timestamp": time.time(),
        "query": query,
        "mode": mode,
        "result_count": result_count,
        "sources": sources,
    }
    
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as exc:
        logger.debug("History save failed: %s", exc)


def load_history() -> List[Dict[str, Any]]:
    """Load search history."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.debug("History load failed: %s", exc)
    return []


def get_analytics() -> Dict[str, Any]:
    """Get search analytics."""
    history = load_history()
    
    if not history:
        return {"total_searches": 0}
    
    total = len(history)
    sources_used = {}
    modes_used = {}
    
    for entry in history:
        mode = entry.get("mode", "unknown")
        modes_used[mode] = modes_used.get(mode, 0) + 1
        
        for source in entry.get("sources", {}):
            sources_used[source] = sources_used.get(source, 0) + 1
    
    return {
        "total_searches": total,
        "modes_used": modes_used,
        "sources_used": sources_used,
        "recent_queries": [e["query"] for e in history[:5]],
    }
