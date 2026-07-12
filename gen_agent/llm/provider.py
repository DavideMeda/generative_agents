"""
Abstract LLM provider interface and factory.

Usage:
    provider = get_llm_provider()          # reads LLM_PROVIDER env var
    text = provider.complete("Say hello")  # returns string
    dialogue = DialogueEngine(llm=provider.complete, ...)
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Base class for all LLM backends."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Send a prompt and return the generated text."""
        ...

    def is_available(self) -> bool:
        """Return True if the backend is reachable. Override for health checks."""
        return True


def get_llm_provider(name: str | None = None) -> LLMProvider:
    """
    Factory that returns a provider by name (or from LLM_PROVIDER env var).

    Supported values: ollama | openrouter | council | mock
    Falls back to mock if the requested provider is unavailable.
    """
    selected = (name or os.getenv("LLM_PROVIDER") or "mock").lower().strip()

    if selected == "ollama":
        from gen_agent.llm.ollama_provider import OllamaProvider
        return OllamaProvider()

    if selected == "openrouter":
        from gen_agent.llm.openrouter_provider import OpenRouterProvider
        return OpenRouterProvider()

    if selected == "council":
        from gen_agent.llm.council import LLMCouncil
        from gen_agent.llm.ollama_provider import OllamaProvider
        from gen_agent.llm.openrouter_provider import OpenRouterProvider
        providers: list[LLMProvider] = []
        try:
            providers.append(OllamaProvider())
        except Exception:
            pass
        try:
            providers.append(OpenRouterProvider())
        except Exception:
            pass
        if providers:
            return LLMCouncil(providers)
        # fallthrough to mock if no providers available

    from gen_agent.llm.mock_provider import MockProvider
    return MockProvider()
