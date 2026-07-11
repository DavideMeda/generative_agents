"""LLM-based structured daily plan for agents (legacy-compatible shape)."""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

LLMCallable = Callable[[str], str]


def build_plan_prompt(
    agent_name: str,
    memories: list[str],
    tick: int,
    location: str,
    poi_names: list[str] | None = None,
) -> str:
    mem = "\n".join(f"- {m}" for m in memories[:8]) or "None"
    places = ""
    if poi_names:
        places = (
            "\nAvailable places — use ONLY these exact names in your plan:\n"
            + ", ".join(poi_names)
            + "\n"
        )
    return (
        f"You are {agent_name}. Tick {tick}. Current area: {location}.\n"
        f"Recent memories:\n{mem}\n"
        f"{places}\n"
        "Write a short daily plan (3-5 concrete actions) as JSON in English only.\n"
        'Each action must use "go to the <place>" or "visit the <place>" with a name from the list.\n'
        '{"plan": ["go to the Cafe", "visit the Park", ...], "focus": "social"}\n'
        "Reply with JSON only. No Italian."
    )


def parse_plan_response(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    # fallback: treat whole text as plan prose
    return {"plan": [text[:200]], "focus": "explore"}


def generate_structured_plan(
    llm: LLMCallable | None,
    agent_name: str,
    memories: list[str],
    tick: int,
    location: str = "town",
    poi_names: list[str] | None = None,
) -> dict[str, Any]:
    if llm is None:
        dest = (poi_names or ["town"])[0] if poi_names else location
        return {"plan": [f"{agent_name} goes to the {dest}"], "focus": "idle", "stub": True}
    prompt = build_plan_prompt(agent_name, memories, tick, location, poi_names=poi_names)
    try:
        raw = llm(prompt)
    except Exception as exc:
        logger.warning("structured plan LLM failed: %s", exc)
        return {"plan": [], "error": str(exc)}
    parsed = parse_plan_response(raw)
    if isinstance(parsed.get("plan"), list):
        parsed["plan_text"] = " ".join(str(p) for p in parsed["plan"])
    else:
        parsed["plan_text"] = str(parsed.get("plan", ""))
    return parsed
