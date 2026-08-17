# -*- coding: utf-8 -*-
"""Agent Search Lite — Search templates and full-text search.

Predefined query patterns and content search utilities.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Predefined search templates
TEMPLATES: Dict[str, Dict[str, Any]] = {
    "latest_news": {
        "name": "Latest News",
        "description": "Get the latest news on a topic",
        "query": "{topic} latest news 2026",
        "mode": "news",
        "limit": 5,
    },
    "code_search": {
        "name": "Code Search",
        "description": "Find code repositories and examples",
        "query": "{topic} language:{lang}",
        "mode": "code",
        "site": "github.com",
        "limit": 5,
    },
    "academic_paper": {
        "name": "Academic Paper",
        "description": "Find academic papers and research",
        "query": "{topic} research paper arxiv",
        "mode": "academic",
        "limit": 5,
    },
    "community_discussion": {
        "name": "Community Discussion",
        "description": "Find discussions and opinions",
        "query": "{topic} discussion",
        "mode": "community",
        "limit": 5,
    },
    "documentation": {
        "name": "Documentation",
        "description": "Find official documentation",
        "query": "{topic} documentation",
        "mode": "code",
        "site": "developer.mozilla.org",
        "limit": 3,
    },
    "comparison": {
        "name": "Comparison",
        "description": "Compare multiple options",
        "query": "{topic} vs {topic2} comparison",
        "mode": "general",
        "limit": 5,
    },
    "tutorial": {
        "name": "Tutorial",
        "description": "Find tutorials and guides",
        "query": "{topic} tutorial guide",
        "mode": "general",
        "limit": 5,
    },
    "error_fix": {
        "name": "Error Fix",
        "description": "Find solutions to errors",
        "query": "{topic} error fix stackoverflow",
        "mode": "code",
        "site": "stackoverflow.com",
        "limit": 5,
    },
}


def get_template_names() -> List[str]:
    """Get list of template names."""
    return list(TEMPLATES.keys())


def get_template(name: str) -> Optional[Dict[str, Any]]:
    """Get a template by name."""
    return TEMPLATES.get(name)


def apply_template(name: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Apply a template with parameters."""
    template = TEMPLATES.get(name)
    if not template:
        return None
    
    query = template["query"].format(**kwargs)
    
    return {
        "query": query,
        "mode": template.get("mode", "general"),
        "site": template.get("site"),
        "limit": template.get("limit", 5),
    }


def search_content(content: str, search_term: str, context_chars: int = 100) -> List[Dict[str, Any]]:
    """Search within content and return matching snippets with context."""
    results = []
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
    
    for match in pattern.finditer(content):
        start = max(0, match.start() - context_chars)
        end = min(len(content), match.end() + context_chars)
        
        snippet = content[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        results.append({
            "snippet": snippet,
            "position": match.start(),
            "match": match.group(),
        })
    
    return results


def compare_results(results1: List[Dict], results2: List[Dict]) -> Dict[str, Any]:
    """Compare two sets of results."""
    urls1 = {r.get("url") for r in results1}
    urls2 = {r.get("url") for r in results2}
    
    common = urls1 & urls2
    only1 = urls1 - urls2
    only2 = urls2 - urls1
    
    return {
        "common_urls": list(common),
        "only_first": list(only1),
        "only_second": list(only2),
        "similarity": len(common) / max(len(urls1 | urls2), 1),
    }
