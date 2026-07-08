"""
Memory privacy classifier — labels memories without requiring an LLM.

Classification via keyword matching:
  private    — health, personal secrets, emotional crises
  restricted — personal opinions, relationship issues
  public     — observations about the world, POI visits, shared events
"""
from __future__ import annotations

from typing import List

_PRIVATE_KEYWORDS = frozenset([
    "secret", "health", "sick", "ill", "medical", "diagnosis",
    "afraid", "ashamed", "embarrass", "private", "confidential",
    "hurt", "trauma", "suicid", "abuse", "suffer",
])

_RESTRICTED_KEYWORDS = frozenset([
    "opinion", "think", "believe", "feel", "relationship",
    "argument", "conflict", "disagree", "angry", "jealous",
    "love", "hate", "resent",
])


def classify(content: str) -> str:
    """
    Return 'private', 'restricted', or 'public'.
    Checks substrings so partial matches work (e.g. 'ill' matches 'illness').
    """
    lower = content.lower()
    for kw in _PRIVATE_KEYWORDS:
        if kw in lower:
            return "private"
    for kw in _RESTRICTED_KEYWORDS:
        if kw in lower:
            return "restricted"
    return "public"
