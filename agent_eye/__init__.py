# -*- coding: utf-8 -*-
"""AgentEye — Complete Internet Data Access for AI Agents.

Zero API keys. Zero cost. 80+ free backends.

Copyright (c) 2026 AgentEye Contributors.
Based on Agent Reach by Panniantong (MIT licensed).
See LICENSE for details.
"""

__version__ = "6.4.0"
__author__ = "AgentEye Contributors"
__license__ = "MIT"

from agent_eye.core import AgentSearchLite, STRATEGY_MODES, interactive_mode
from agent_eye.exceptions import (
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
from agent_eye.extractors import smart_extract, score_readability
from agent_eye.ranking import (
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
