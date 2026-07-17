"""
Circuit breaker for LLM providers.

Wraps any LLMProvider and opens the circuit after N consecutive failures,
preventing the simulation from hanging on every call when the LLM is down.

States:
    CLOSED    — normal operation, all calls forwarded to provider
    OPEN      — fail-fast, returns cached error without calling provider
    HALF_OPEN — one probe call; CLOSED on success, OPEN on failure

Usage:
    from gen_agent.llm.circuit_breaker import CircuitBreaker
    from gen_agent.llm.ollama_provider import OllamaProvider

    provider = CircuitBreaker(OllamaProvider(), failure_threshold=3, recovery_timeout=30.0)
    text = provider.complete("Say hello")
"""
from __future__ import annotations

import logging
import time

from gen_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

_ERROR_MARKERS = ("[ollama", "[openrouter", "[circuit", "[llm", "[stub")


def _is_error_response(text: str) -> bool:
    """Return True if the provider returned a fallback error string."""
    lower = text.lower()
    return any(marker in lower for marker in _ERROR_MARKERS)


class CircuitBreaker(LLMProvider):
    """
    Wraps an LLMProvider with circuit breaker semantics.

    failure_threshold  — consecutive failures before circuit opens (default 3)
    recovery_timeout   — seconds to wait before probing again (default 30)
    """

    def __init__(
        self,
        provider: LLMProvider,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._provider = provider
        self._threshold = failure_threshold
        self._timeout = recovery_timeout
        self._failures = 0
        self._state = "CLOSED"   # "CLOSED" | "OPEN" | "HALF_OPEN"
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        return self._state

    def _try_recover(self) -> None:
        """Transition OPEN → HALF_OPEN when recovery_timeout has elapsed."""
        if self._state == "OPEN" and time.monotonic() - self._opened_at >= self._timeout:
            self._state = "HALF_OPEN"
            logger.info("CircuitBreaker: entering HALF_OPEN — probing LLM")

    def _on_success(self) -> None:
        if self._state in ("HALF_OPEN", "OPEN"):
            logger.info("CircuitBreaker: CLOSED — LLM recovered")
        self._failures = 0
        self._state = "CLOSED"

    def _on_failure(self, reason: str) -> None:
        self._failures += 1
        if self._failures >= self._threshold or self._state == "HALF_OPEN":
            self._state = "OPEN"
            self._opened_at = time.monotonic()
            logger.warning(
                "CircuitBreaker: OPEN after %d failures — reason: %s",
                self._failures, reason,
            )

    def complete(self, prompt: str) -> str:
        self._try_recover()

        if self._state == "OPEN":
            return "[Circuit breaker open: LLM temporarily unavailable — retrying later]"

        try:
            result = self._provider.complete(prompt)
        except Exception as exc:
            self._on_failure(str(exc))
            return f"[LLM call failed: {exc}]"

        if _is_error_response(result):
            self._on_failure(result[:80])
            return result

        self._on_success()
        return result

    def is_available(self) -> bool:
        self._try_recover()
        if self._state == "OPEN":
            return False
        return self._provider.is_available()
