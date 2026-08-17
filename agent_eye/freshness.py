# -*- coding: utf-8 -*-
"""AgentEye — Freshness/recency scoring (Google's recency signal, simplified).

Pure date parsing from result text. No APIs, no network calls.

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Date patterns — ordered from most specific to least specific.
# Each is (regex, parser_function).
# ---------------------------------------------------------------------------

def _month_num(name: str) -> int:
    months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
              "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    return months.get(name.lower()[:3], 1)


def _parse_iso(groups: tuple) -> datetime:
    return datetime(int(groups[0]), int(groups[1]), int(groups[2]))


def _parse_month_first(groups: tuple) -> datetime:
    return datetime(int(groups[2]), _month_num(groups[0]), int(groups[1]))


def _parse_day_first(groups: tuple) -> datetime:
    return datetime(int(groups[2]), _month_num(groups[1]), int(groups[0]))


def _parse_slash(groups: tuple) -> datetime:
    return datetime(int(groups[0]), int(groups[1]), int(groups[2]))


def _parse_relative(groups: tuple) -> datetime:
    n, unit = int(groups[0]), groups[1]
    deltas = {
        "minute": timedelta(minutes=n), "hour": timedelta(hours=n),
        "day": timedelta(days=n), "week": timedelta(weeks=n),
        "month": timedelta(days=n * 30), "year": timedelta(days=n * 365),
    }
    return datetime.now() - deltas.get(unit, timedelta(days=n))


def _parse_year_only(groups: tuple) -> datetime:
    return datetime(int(groups[0]), 1, 1)


DATE_PATTERNS: list[tuple[str, Callable]] = [
    # ISO: 2026-01-15
    (r'\b(\d{4})-(\d{2})-(\d{2})\b', _parse_iso),
    # Month first: Jan 15, 2026 / January 15, 2026
    (r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2}),? (\d{4})\b',
     _parse_month_first),
    # Day first: 15 Jan 2026
    (r'\b(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{4})\b',
     _parse_day_first),
    # Slash: 2026/01/15
    (r'\b(\d{4})/(\d{2})/(\d{2})\b', _parse_slash),
    # Relative: 3 days ago, 2 hours ago
    (r'\b(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago\b', _parse_relative),
    # Year only: 2026
    (r'\b(20\d{2})\b', _parse_year_only),
]


def freshness_score(title: str, description: str = "") -> float:
    """Return 0.0-1.0 freshness score.

    1.0 = today, 0.0 = >5 years old. Unknown date = 0.5 (neutral).
    """
    text = f"{title} {description}"
    now = datetime.now()

    best_date: Optional[datetime] = None
    for pattern, parser in DATE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                date = parser(m.groups())
                if best_date is None or date > best_date:
                    best_date = date
            except (ValueError, IndexError):
                continue

    if best_date is None:
        return 0.5  # unknown date = neutral

    days_old = (now - best_date).days
    if days_old < 0:
        return 0.5  # future date = suspicious
    if days_old < 1:
        return 1.0    # today
    if days_old < 7:
        return 0.95   # this week
    if days_old < 30:
        return 0.85  # this month
    if days_old < 90:
        return 0.7   # this quarter
    if days_old < 365:
        return 0.5  # this year
    if days_old < 730:
        return 0.3  # 2 years
    return 0.1  # old


def is_time_sensitive_query(query: str) -> bool:
    """Detect if query needs fresh results."""
    fresh_keywords = {
        "latest", "new", "recent", "today", "now", "current",
        "2026", "2025", "this year", "this week", "update",
        "news", "trending", "breaking", "just released",
        "announced", "released", "yesterday", "tomorrow",
    }
    return any(k in query.lower() for k in fresh_keywords)
