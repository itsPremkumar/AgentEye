# -*- coding: utf-8 -*-
"""Agent Search Lite — User agent rotation and rate limiting.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import collections
import logging
import random
import threading
import time
from typing import Any, Deque, Dict, Optional

logger = logging.getLogger(__name__)

# User agent pool
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Agent Search Lite (our own)
    "Mozilla/5.0 (compatible; agent-search-lite/3.1; +https://github.com/itsPremkumar/agent-search-lite)",
]

# Domain reliability scores (0.0 to 1.0)
DOMAIN_RELIABILITY: Dict[str, float] = {
    # Tier 1: Highly reliable
    "github.com": 0.95,
    "stackoverflow.com": 0.95,
    "wikipedia.org": 0.95,
    "arxiv.org": 0.95,
    "news.ycombinator.com": 0.9,
    "docs.python.org": 0.95,
    "developer.mozilla.org": 0.95,
    
    # Tier 2: Generally reliable
    "medium.com": 0.7,
    "dev.to": 0.75,
    "lemmy.world": 0.7,
    "lemmy.ml": 0.7,
    "reddit.com": 0.6,
    
    # Tier 3: Variable
    "duckduckgo.com": 0.5,
    "jina.ai": 0.5,
}


class UserAgentRotator:
    """Rotates user agents to avoid blocking."""
    
    def __init__(self):
        self._agents = USER_AGENTS.copy()
        self._index = 0
        self._lock = threading.Lock()
    
    def get(self) -> str:
        """Get next user agent in rotation."""
        with self._lock:
            agent = self._agents[self._index]
            self._index = (self._index + 1) % len(self._agents)
            return agent
    
    def get_random(self) -> str:
        """Get random user agent."""
        return random.choice(self._agents)


class RateLimiter:
    """Self-throttling rate limiter per domain.
    
    Tracks request timestamps and enforces minimum intervals
    to avoid getting 429 (Too Many Requests).
    """
    
    def __init__(self, min_interval: float = 1.0, max_per_minute: int = 30):
        self.min_interval = min_interval
        self.max_per_minute = max_per_minute
        self._requests: Dict[str, Deque[float]] = collections.defaultdict(
            lambda: collections.deque(maxlen=max_per_minute)
        )
        self._lock = threading.Lock()
    
    def wait_if_needed(self, domain: str) -> None:
        """Wait if we're hitting the domain too fast."""
        with self._lock:
            now = time.time()
            timestamps = self._requests[domain]
            
            if timestamps:
                elapsed = now - timestamps[-1]
                if elapsed < self.min_interval:
                    sleep_time = self.min_interval - elapsed
                    logger.debug("Rate limiting %s: sleeping %.2fs", domain, sleep_time)
                    time.sleep(sleep_time)
            
            self._requests[domain].append(now)
    
    def get_stats(self) -> Dict[str, int]:
        """Get request counts per domain."""
        with self._lock:
            return {domain: len(times) for domain, times in self._requests.items()}


class ReliabilityScorer:
    """Scores sources by reliability."""
    
    @staticmethod
    def get_domain(url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.hostname
        except Exception:
            return None
    
    @staticmethod
    def get_score(url: str) -> float:
        """Get reliability score for a URL (0.0 to 1.0)."""
        domain = ReliabilityScorer.get_domain(url)
        if not domain:
            return 0.5
        
        # Check exact domain
        if domain in DOMAIN_RELIABILITY:
            return DOMAIN_RELIABILITY[domain]
        
        # Check parent domain
        parts = domain.split(".")
        if len(parts) > 2:
            parent = ".".join(parts[-2:])
            if parent in DOMAIN_RELIABILITY:
                return DOMAIN_RELIABILITY[parent]
        
        return 0.5  # Default for unknown domains
    
    @staticmethod
    def score_results(results: list) -> list:
        """Add reliability_score to each result."""
        for r in results:
            r["reliability_score"] = ReliabilityScorer.get_score(r.get("url", ""))
        return results


# Global instances
ua_rotator = UserAgentRotator()
rate_limiter = RateLimiter(min_interval=0.5, max_per_minute=20)
reliability_scorer = ReliabilityScorer()
