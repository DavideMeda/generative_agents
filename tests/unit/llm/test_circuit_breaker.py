"""Unit tests for CircuitBreaker — covers all three states (CLOSED, OPEN, HALF_OPEN)."""
from __future__ import annotations

import time

from gen_agent.llm.circuit_breaker import CircuitBreaker, _is_error_response
from gen_agent.llm.provider import LLMProvider

# ---------------------------------------------------------------------------
# Minimal stub provider
# ---------------------------------------------------------------------------

class _OkProvider(LLMProvider):
    def complete(self, prompt: str) -> str:
        return "hello"

    def is_available(self) -> bool:
        return True


class _FailProvider(LLMProvider):
    def complete(self, prompt: str) -> str:
        raise RuntimeError("connection refused")

    def is_available(self) -> bool:
        return False


class _ErrorResponseProvider(LLMProvider):
    """Returns a valid string but one that looks like an error marker."""

    def complete(self, prompt: str) -> str:
        return "[ollama error 500]"

    def is_available(self) -> bool:
        return True


class _ToggleProvider(LLMProvider):
    """Fails `fail_count` times, then succeeds."""

    def __init__(self, fail_count: int) -> None:
        self._remaining = fail_count

    def complete(self, prompt: str) -> str:
        if self._remaining > 0:
            self._remaining -= 1
            raise RuntimeError("transient failure")
        return "recovered"

    def is_available(self) -> bool:
        return self._remaining == 0


# ---------------------------------------------------------------------------
# _is_error_response
# ---------------------------------------------------------------------------

class TestIsErrorResponse:
    def test_clean_response(self):
        assert _is_error_response("Hello, how are you?") is False

    def test_ollama_error_marker(self):
        assert _is_error_response("[Ollama Error 500]") is True

    def test_openrouter_marker(self):
        assert _is_error_response("[OpenRouter 429 rate limit]") is True

    def test_circuit_marker(self):
        assert _is_error_response("[circuit breaker open]") is True

    def test_stub_marker(self):
        assert _is_error_response("[stub response]") is True

    def test_partial_text_with_marker(self):
        assert _is_error_response("Response: [llm unavailable]") is True


# ---------------------------------------------------------------------------
# CLOSED state — happy path
# ---------------------------------------------------------------------------

class TestCircuitBreakerClosed:
    def test_forwards_to_provider(self):
        cb = CircuitBreaker(_OkProvider(), failure_threshold=3)
        result = cb.complete("ping")
        assert result == "hello"
        assert cb.state == "CLOSED"

    def test_is_available_delegates(self):
        cb = CircuitBreaker(_OkProvider())
        assert cb.is_available() is True

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(_OkProvider(), failure_threshold=3)
        # induce 2 failures (below threshold)
        cb._failures = 2
        cb.complete("ping")
        assert cb._failures == 0

    def test_error_response_counts_as_failure(self):
        cb = CircuitBreaker(_ErrorResponseProvider(), failure_threshold=3)
        cb.complete("ping")
        assert cb._failures == 1

    def test_exception_counts_as_failure(self):
        cb = CircuitBreaker(_FailProvider(), failure_threshold=3)
        result = cb.complete("ping")
        assert "[LLM call failed" in result
        assert cb._failures == 1


# ---------------------------------------------------------------------------
# OPEN state — fail-fast
# ---------------------------------------------------------------------------

class TestCircuitBreakerOpen:
    def _open_circuit(self, threshold: int = 3) -> CircuitBreaker:
        cb = CircuitBreaker(_FailProvider(), failure_threshold=threshold, recovery_timeout=9999.0)
        for _ in range(threshold):
            cb.complete("ping")
        return cb

    def test_opens_after_threshold_failures(self):
        cb = self._open_circuit(threshold=3)
        assert cb.state == "OPEN"

    def test_open_returns_without_calling_provider(self):
        cb = self._open_circuit(threshold=2)
        result = cb.complete("any prompt")
        assert "Circuit breaker open" in result

    def test_is_available_false_when_open(self):
        cb = self._open_circuit()
        assert cb.is_available() is False

    def test_single_failure_does_not_open(self):
        cb = CircuitBreaker(_FailProvider(), failure_threshold=3, recovery_timeout=9999.0)
        cb.complete("ping")
        assert cb.state == "CLOSED"


# ---------------------------------------------------------------------------
# HALF_OPEN state — recovery probe
# ---------------------------------------------------------------------------

class TestCircuitBreakerHalfOpen:
    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(_FailProvider(), failure_threshold=1, recovery_timeout=0.0)
        cb.complete("ping")                    # opens the circuit
        assert cb.state == "OPEN"
        time.sleep(0.01)                       # recovery_timeout elapsed
        cb._try_recover()
        assert cb.state == "HALF_OPEN"

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker(_ToggleProvider(fail_count=1), failure_threshold=1, recovery_timeout=0.0)
        cb.complete("ping")                    # fails → OPEN
        time.sleep(0.01)
        result = cb.complete("probe")          # succeeds → CLOSED
        assert result == "recovered"
        assert cb.state == "CLOSED"
        assert cb._failures == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(_FailProvider(), failure_threshold=1, recovery_timeout=0.0)
        cb.complete("ping")                    # fails → OPEN
        time.sleep(0.01)
        cb._try_recover()                      # → HALF_OPEN
        assert cb.state == "HALF_OPEN"
        cb.complete("probe")                   # fails again → OPEN
        assert cb.state == "OPEN"


# ---------------------------------------------------------------------------
# is_available delegates to provider when CLOSED
# ---------------------------------------------------------------------------

class TestIsAvailable:
    def test_closed_delegates_to_provider(self):
        cb = CircuitBreaker(_OkProvider())
        assert cb.is_available() is True

    def test_closed_unavailable_provider(self):
        cb = CircuitBreaker(_FailProvider())
        assert cb.is_available() is False

    def test_open_always_unavailable(self):
        cb = CircuitBreaker(_OkProvider(), failure_threshold=1)
        cb._state = "OPEN"
        cb._opened_at = time.monotonic()
        assert cb.is_available() is False
