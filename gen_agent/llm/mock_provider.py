"""
Mock LLM provider — deterministic, no network.
Used in CI, unit tests, and offline development.
"""
from __future__ import annotations

import hashlib

from gen_agent.llm.provider import LLMProvider

_RESPONSES = [
    "That is a very interesting perspective, I hadn't considered it that way.",
    "I agree, though I think we should also look at the broader implications.",
    "Let me think about this more carefully before responding.",
    "That makes sense given the current situation we're all facing.",
    "I appreciate you sharing that with me, it gives me a lot to think about.",
    "We should probably discuss this further with the others in the group.",
    "I'm not entirely sure I understand — could you elaborate a bit more?",
    "That's exactly what I was thinking. We are in complete agreement on this.",
]


class MockProvider(LLMProvider):
    """
    Returns canned responses selected by hashing the prompt.
    Deterministic: same prompt always returns the same response.
    """

    def complete(self, prompt: str) -> str:
        idx = int(hashlib.md5(prompt.encode()).hexdigest(), 16) % len(_RESPONSES)
        return _RESPONSES[idx]

    def is_available(self) -> bool:
        return True
