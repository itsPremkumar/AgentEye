# -*- coding: utf-8 -*-
"""Agent Search Lite — Retry utilities and decorators.

Provides exponential backoff retry for rate-limited endpoints.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, Optional, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_status: tuple = (429, 500, 502, 503, 504),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_status = retry_on_status


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay with exponential backoff and optional jitter."""
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)
    if config.jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    return delay


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on_status: tuple = (429, 500, 502, 503, 504),
):
    """Decorator for retrying async functions with exponential backoff."""
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on_status=retry_on_status,
    )
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except httpx.HTTPStatusError as exc:
                    last_exception = exc
                    if exc.response.status_code not in config.retry_on_status:
                        raise
                    if attempt == config.max_retries:
                        raise
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    last_exception = exc
                    if attempt == config.max_retries:
                        raise
                
                delay = calculate_delay(attempt, config)
                logger.debug(
                    "Retry %d/%d for %s after %.1fs",
                    attempt + 1,
                    config.max_retries,
                    func.__name__,
                    delay,
                )
                await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_sync(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on_status: tuple = (429, 500, 502, 503, 504),
):
    """Decorator for retrying sync functions with exponential backoff."""
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on_status=retry_on_status,
    )
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as exc:
                    last_exception = exc
                    if exc.response.status_code not in config.retry_on_status:
                        raise
                    if attempt == config.max_retries:
                        raise
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    last_exception = exc
                    if attempt == config.max_retries:
                        raise
                
                delay = calculate_delay(attempt, config)
                logger.debug(
                    "Retry %d/%d for %s after %.1fs",
                    attempt + 1,
                    config.max_retries,
                    func.__name__,
                    delay,
                )
                time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator
