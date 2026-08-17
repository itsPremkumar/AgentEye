# -*- coding: utf-8 -*-
"""AgentEye — Circuit Breaker pattern for backend resilience.

Tracks per-backend failures and temporarily disables backends that
consecutively fail, preventing slow waits on broken/hanging services.

States:
    CLOSED   — normal operation, requests flow through
    OPEN     — backend disabled, requests instantly skipped
    HALF_OPEN — after cooldown, one trial request allowed

Copyright (c) 2026 AgentEye Contributors.
MIT License. See LICENSE for details.
"""
from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # Normal
    OPEN = "open"           # Disabled (failing)
    HALF_OPEN = "half_open" # Trial after cooldown


class CircuitBreaker:
    """Per-backend circuit breaker with automatic recovery.

    After *failure_threshold* consecutive failures, a backend is disabled
    (OPEN) for *recovery_timeout* seconds. Then it enters HALF_OPEN and
    allows one trial request. Success → CLOSED, failure → OPEN again.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 300.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._states: Dict[str, CircuitState] = {}
        self._failures: Dict[str, int] = {}
        self._opened_at: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_available(self, name: str) -> bool:
        """Return True if the backend is allowed to be called."""
        with self._lock:
            state = self._states.get(name, CircuitState.CLOSED)

            if state == CircuitState.CLOSED:
                return True

            if state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                opened_at = self._opened_at.get(name, 0)
                if time.time() - opened_at >= self.recovery_timeout:
                    self._states[name] = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker %s → HALF_OPEN (trial)", name)
                    return True
                return False

            # HALF_OPEN — allow one trial
            return True

    def record_success(self, name: str) -> None:
        """Record a successful call → reset to CLOSED."""
        with self._lock:
            self._states[name] = CircuitState.CLOSED
            self._failures[name] = 0

    def record_failure(self, name: str) -> None:
        """Record a failed call. Trip to OPEN if threshold reached."""
        with self._lock:
            failures = self._failures.get(name, 0) + 1
            self._failures[name] = failures

            if failures >= self.failure_threshold:
                self._states[name] = CircuitState.OPEN
                self._opened_at[name] = time.time()
                logger.warning(
                    "Circuit breaker %s → OPEN after %d failures (disabled for %ds)",
                    name, failures, int(self.recovery_timeout),
                )

    def get_state(self, name: str) -> CircuitState:
        """Return current state of a backend."""
        with self._lock:
            return self._states.get(name, CircuitState.CLOSED)

    def get_stats(self) -> Dict[str, dict]:
        """Return status of all known backends."""
        with self._lock:
            return {
                name: {
                    "state": state.value,
                    "failures": self._failures.get(name, 0),
                    "opened_at": self._opened_at.get(name),
                }
                for name, state in self._states.items()
            }

    def reset(self, name: Optional[str] = None) -> None:
        """Reset one or all backends to CLOSED."""
        with self._lock:
            if name:
                self._states[name] = CircuitState.CLOSED
                self._failures[name] = 0
                self._opened_at.pop(name, None)
            else:
                self._states.clear()
                self._failures.clear()
                self._opened_at.clear()


# Global instance
circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=300.0)
