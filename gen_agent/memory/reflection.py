"""
Reflection engine — generates summary reflections from a list of memory records.
Ported slim from Gen_Agent legacy UniversalMemoryManager._trigger_reflection.

The LLM is optional: if none is provided, a template-based reflection is generated.
"""
from __future__ import annotations

import random
import time
from typing import Any, Callable, List, Optional

LLMCallable = Callable[[str], str]

_POSITIVE_TEMPLATES = [
    "Reflecting on recent interactions, I notice a positive pattern in my social connections.",
    "My recent experiences have been mostly constructive and rewarding.",
    "I am building meaningful relationships in this community.",
]
_NEGATIVE_TEMPLATES = [
    "Reflecting on recent challenges, I recognize the need for adaptation.",
    "My recent experiences have taught me the importance of resilience.",
    "I am learning to handle complex social situations more effectively.",
]
_NEUTRAL_TEMPLATES = [
    "Reflecting on my recent experiences, I observe an interesting balance.",
    "My latest interactions show a variety of perspectives worth considering.",
    "I am developing a more nuanced understanding of the people around me.",
]


def generate_reflection(
    agent_id: str,
    agent_name: str,
    memories: List[Any],  # List[MemoryRecord]
    llm: Optional[LLMCallable] = None,
) -> str:
    """Return a reflection string from the top memories."""
    if not memories:
        return f"{agent_name} pauses to reflect, but finds little to think about yet."

    contents = [getattr(m, "content", str(m)) for m in memories[:5]]
    importances = [float(getattr(m, "importance", 5.0)) for m in memories[:5]]
    avg_imp = sum(importances) / len(importances) if importances else 5.0

    if llm is not None:
        prompt = _build_reflection_prompt(agent_name, contents)
        try:
            result = llm(prompt).strip()
            if result and len(result.split()) >= 8:
                return result
        except Exception:
            pass

    # Template fallback
    if avg_imp > 7.0:
        templates = _POSITIVE_TEMPLATES
    elif avg_imp < 4.0:
        templates = _NEGATIVE_TEMPLATES
    else:
        templates = _NEUTRAL_TEMPLATES

    base = random.choice(templates)
    snippet = contents[0][:80] + ("..." if len(contents[0]) > 80 else "")
    return f"{base} Particularly notable: {snippet}"


def _build_reflection_prompt(agent_name: str, contents: List[str]) -> str:
    items = "\n".join(f"- {c[:120]}" for c in contents)
    return (
        f"You are {agent_name}. Write a single brief reflective thought (2-3 sentences, "
        f"first person, past tense) summarizing what you learned or felt from these recent memories:\n"
        f"{items}\n\n"
        f"Write in English only. Be specific, introspective, and natural. "
        f"Do NOT mention 'simulation', 'AI', or anything meta. Start directly with 'I' or 'My'.\n"
        f"{agent_name}:"
    )
