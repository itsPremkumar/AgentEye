"""Tests for the Circuit Breaker pattern."""
from __future__ import annotations

import time
import pytest
from agent_eye.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.is_available("any_backend") is True
        assert cb.get_state("any_backend") == CircuitState.CLOSED

    def test_trips_to_open_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("backend_a")
        cb.record_failure("backend_a")
        assert cb.is_available("backend_a") is True  # still CLOSED
        cb.record_failure("backend_a")
        assert cb.is_available("backend_a") is False  # now OPEN
        assert cb.get_state("backend_a") == CircuitState.OPEN

    def test_recovery_to_half_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.3)
        cb.record_failure("backend_b")
        cb.record_failure("backend_b")
        assert cb.get_state("backend_b") == CircuitState.OPEN
        time.sleep(0.5)
        # is_available triggers the transition to HALF_OPEN
        assert cb.is_available("backend_b") is True
        assert cb.get_state("backend_b") == CircuitState.HALF_OPEN

    def test_success_resets_to_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("backend_c")
        cb.record_failure("backend_c")
        cb.record_success("backend_c")
        assert cb.get_state("backend_c") == CircuitState.CLOSED
        assert cb.is_available("backend_c") is True

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.3)
        cb.record_failure("backend_d")
        cb.record_failure("backend_d")
        time.sleep(0.5)
        # Trigger transition to HALF_OPEN
        assert cb.is_available("backend_d") is True
        assert cb.get_state("backend_d") == CircuitState.HALF_OPEN
        # Success in HALF_OPEN → CLOSED
        cb.record_success("backend_d")
        assert cb.get_state("backend_d") == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.3)
        cb.record_failure("backend_e")
        cb.record_failure("backend_e")
        time.sleep(0.5)
        # Trigger transition to HALF_OPEN
        assert cb.is_available("backend_e") is True
        assert cb.get_state("backend_e") == CircuitState.HALF_OPEN
        # Failure in HALF_OPEN → OPEN again
        cb.record_failure("backend_e")
        assert cb.get_state("backend_e") == CircuitState.OPEN

    def test_get_stats(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("x")
        cb.record_failure("x")  # trips to OPEN
        cb.record_failure("y")
        cb.record_failure("y")  # trips to OPEN
        stats = cb.get_stats()
        assert "x" in stats
        assert "y" in stats
        assert stats["x"]["state"] == "open"
        assert stats["y"]["state"] == "open"

    def test_reset_single(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("z")
        cb.record_failure("z")
        assert cb.get_state("z") == CircuitState.OPEN
        cb.reset("z")
        assert cb.get_state("z") == CircuitState.CLOSED

    def test_reset_all(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("a")
        cb.record_failure("a")
        cb.record_failure("b")
        cb.record_failure("b")
        cb.reset()
        assert cb.get_state("a") == CircuitState.CLOSED
        assert cb.get_state("b") == CircuitState.CLOSED

    def test_global_instance(self):
        from agent_eye.circuit_breaker import circuit_breaker
        assert circuit_breaker is not None
        assert circuit_breaker.failure_threshold == 3
