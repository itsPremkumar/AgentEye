# -*- coding: utf-8 -*-
"""Agent Search Lite — Free web search for AI agents.

Completely free, zero API key required.
Multiple backends with fallback chain.

Usage:
    from agent_search.core import AgentSearchLite
    search = AgentSearchLite()
    result = search.search("query")
"""

__version__ = "2.0.0"
__author__ = "itsPremkumar"

from agent_search.core import AgentSearchLite

__all__ = ["AgentSearchLite"]
