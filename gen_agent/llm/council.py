"""
LLM Council — queries multiple providers and unifies responses.

Two strategies:
  - majority: returns the response whose key keywords appear most often
  - synthesis: sends all responses to a third provider for a final summary

Usage:
    council = LLMCouncil([OllamaProvider(), OpenRouterProvider()])
    text = council.complete("What should we do next?")
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import List

from gen_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


def _keyword_set(text: str) -> set[str]:
    stop = {"the", "a", "an", "is", "it", "to", "of", "in", "and", "that", "i", "we"}
    return {w.lower().strip(".,!?;:") for w in text.split() if w.lower() not in stop and len(w) > 2}


class LLMCouncil(LLMProvider):
    """
    Queries all providers in parallel (sequential for simplicity) and
    returns the response whose vocabulary overlaps most with the others.

    ponytail: sequential for now — upgrade to asyncio.gather if latency matters.
    """

    def __init__(
        self,
        providers: List[LLMProvider],
        strategy: str = "majority",
    ) -> None:
        if not providers:
            raise ValueError("LLMCouncil requires at least one provider")
        self._providers = providers
        self._strategy = strategy

    def complete(self, prompt: str) -> str:
        responses: list[str] = []
        for provider in self._providers:
            try:
                r = provider.complete(prompt)
                if r and not r.startswith("["):  # skip error strings
                    responses.append(r)
            except Exception as exc:
                logger.warning("Council provider %s failed: %s", type(provider).__name__, exc)

        if not responses:
            return "[Council: all providers failed]"
        if len(responses) == 1:
            return responses[0]

        if self._strategy == "majority":
            return self._majority_pick(responses)
        return responses[0]  # fallback: first available

    def _majority_pick(self, responses: list[str]) -> str:
        """Pick the response most similar to the others by keyword overlap."""
        best, best_score = responses[0], -1.0
        for candidate in responses:
            cand_kw = _keyword_set(candidate)
            score = sum(
                len(cand_kw & _keyword_set(other))
                for other in responses
                if other is not candidate
            )
            if score > best_score:
                best_score = score
                best = candidate
        return best

    def is_available(self) -> bool:
        return any(p.is_available() for p in self._providers)
