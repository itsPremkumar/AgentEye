# -*- coding: utf-8 -*-
"""Agent Search Lite — Custom exceptions and error types.

This module defines all custom exceptions used throughout the project
for proper error handling and graceful degradation.
"""


class AgentSearchError(Exception):
    """Base exception for all Agent Search Lite errors."""

    def __init__(self, message: str, *, backend: str = None, original_error: Exception = None):
        self.backend = backend
        self.original_error = original_error
        super().__init__(message)


class BackendError(AgentSearchError):
    """Raised when a search backend fails."""

    def __init__(self, backend: str, message: str, *, original_error: Exception = None):
        self.backend = backend
        super().__init__(
            f"Backend '{backend}' failed: {message}",
            backend=backend,
            original_error=original_error,
        )


class AllBackendsFailedError(AgentSearchError):
    """Raised when all search backends fail."""

    def __init__(self, errors: dict):
        self.errors = errors
        backend_list = ", ".join(errors.keys())
        super().__init__(
            f"All search backends failed: {backend_list}. "
            f"Try again later or check your network connection."
        )


class InvalidURLError(AgentSearchError):
    """Raised when an invalid URL is provided."""

    def __init__(self, url: str):
        self.url = url
        super().__init__(
            f"Invalid URL: '{url}'. URL must start with http:// or https://"
        )


class InvalidModeError(AgentSearchError):
    """Raised when an invalid strategy mode is provided."""

    def __init__(self, mode: str, valid_modes: list):
        self.mode = mode
        self.valid_modes = valid_modes
        super().__init__(
            f"Invalid mode: '{mode}'. Valid modes are: {', '.join(valid_modes)}"
        )


class CacheError(AgentSearchError):
    """Raised when cache operations fail."""

    def __init__(self, message: str, *, original_error: Exception = None):
        super().__init__(f"Cache error: {message}", original_error=original_error)


class RateLimitError(AgentSearchError):
    """Raised when rate limit is exceeded."""

    def __init__(self, backend: str, retry_after: float = None):
        self.backend = backend
        self.retry_after = retry_after
        msg = f"Rate limit exceeded on backend '{backend}'"
        if retry_after:
            msg += f". Retry after {retry_after:.1f} seconds"
        super().__init__(msg, backend=backend)


class NetworkError(AgentSearchError):
    """Raised when network connection fails."""

    def __init__(self, backend: str, *, original_error: Exception = None):
        super().__init__(
            f"Network error on backend '{backend}': {original_error}. "
            f"Check your internet connection.",
            backend=backend,
            original_error=original_error,
        )


class TimeoutError(AgentSearchError):
    """Raised when a request times out."""

    def __init__(self, backend: str, timeout: float):
        self.backend = backend
        self.timeout = timeout
        super().__init__(
            f"Backend '{backend}' timed out after {timeout:.1f} seconds. "
            f"Try again later or increase timeout.",
            backend=backend,
        )


class ConfigurationError(AgentSearchError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")


class RobotsDisallowedError(AgentSearchError):
    """Raised when a URL is disallowed by the target site's robots.txt.

    Production-grade crawlers must respect robots.txt. We surface this as a
    distinct error so callers (and agents) can report the restriction instead
    of silently fetching content they were asked not to.
    """

    def __init__(self, url: str, rule: str = ""):
        self.url = url
        self.rule = rule
        msg = f"URL disallowed by robots.txt: '{url}'"
        if rule:
            msg += f" (rule: {rule})"
        super().__init__(msg)
