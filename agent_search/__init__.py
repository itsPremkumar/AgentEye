# -*- coding: utf-8 -*-
"""Agent Search Lite — Free web search for AI agents.

Completely free, zero API key required.
Multiple backends with parallel execution.

Copyright (c) 2026 Agent Search Lite Contributors.
Based on Agent Reach by Panniantong (MIT licensed).
See LICENSE for details.
"""

__version__ = "2.1.0"
__author__ = "Agent Search Lite Contributors"
__license__ = "MIT"

from agent_search.core import AgentSearchLite, STRATEGY_MODES
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

__all__ = [
    "AgentSearchLite",
    "STRATEGY_MODES",
    "AgentSearchError",
    "AllBackendsFailedError",
    "BackendError",
    "CacheError",
    "ConfigurationError",
    "InvalidModeError",
    "InvalidURLError",
    "NetworkError",
    "RateLimitError",
    "TimeoutError",
]
