# -*- coding: utf-8 -*-
"""Agent Search Lite — Free Web Search for AI agents.

Completely free, zero API key required.
Multiple backends with parallel execution.

Copyright (c) 2026 Agent Search Lite Contributors.
Based on Agent Reach by Panniantong (MIT licensed).
See LICENSE for details.
"""

__version__ = "3.0.0"
__author__ = "Agent Search Lite Contributors"
__license__ = "MIT"

from agent_search.core import AgentSearchLite, STRATEGY_MODES, interactive_mode
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
from agent_search.extractors import smart_extract, score_readability
from agent_search.ranking import (
    cross_verify,
    rank_results,
    quality_score,
    is_polluted,
    format_token_conscious,
)

__all__ = [
    "AgentSearchLite",
    "STRATEGY_MODES",
    "interactive_mode",
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
    "smart_extract",
    "score_readability",
    "cross_verify",
    "rank_results",
    "quality_score",
    "is_polluted",
    "format_token_conscious",
]
