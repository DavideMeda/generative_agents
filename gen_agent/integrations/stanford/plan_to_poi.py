"""Map natural-language plan goals to world POIs (ported from legacy)."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

# ponytail: static aliases; upgrade path = load from world tags / POI metadata
POI_ALIASES: dict[str, str] = {
    "coffee": "cafe",
    "café": "cafe",
    "shop": "market",
    "shops": "market",
    "downtown": "market",
    "books": "library",
    "reading": "library",
    "town": "townhall",
    "hospital": "hospital",
    "school": "school",
    "park": "park",
}


def _split_goal_candidate(goal: str) -> list[str]:
    parts = re.split(r"\s+(?:and|then|e|poi|dopo)\s+", goal, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def extract_concrete_goals(text: str) -> list[str]:
    if not text:
        return []
    patterns = [
        r"go to (?:the )?([a-z]+(?:\s+[a-z]+)*)",
        r"visit (?:the )?([a-z]+(?:\s+[a-z]+)*)",
        r"move to (?:the )?([a-z]+(?:\s+[a-z]+)*)",
        r"head to (?:the )?([a-z]+(?:\s+[a-z]+)*)",
        r"walk to (?:the )?([a-z]+(?:\s+[a-z]+)*)",
        r"(?:at|in) the ([a-z]+(?:\s+[a-z]+)*)",
    ]
    goals: list[str] = []
    seen: set[str] = set()
    stop = {"and", "or", "the", "a", "il", "la", "di", "da", "in", "un", "una", "with", "friend"}
    for pattern in patterns:
        for match in re.finditer(pattern, text.lower(), re.IGNORECASE):
            goal = " ".join(w for w in match.group(1).split() if w not in stop)
            for atomic in _split_goal_candidate(goal) or [goal]:
                if len(atomic) >= 3 and atomic not in seen:
                    seen.add(atomic)
                    goals.append(atomic)
    return goals


def _keywords_from_text(text: str, *, limit: int = 10) -> list[str]:
    words = [w.strip(" ,.;:!?\"'()[]{}").lower() for w in (text or "").split()]
    words = [w for w in words if 3 <= len(w) <= 18]
    out: list[str] = []
    for w in words:
        if w not in out:
            out.append(w)
        if len(out) >= limit:
            break
    return out


def _fuzzy_match_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _poi_dict(poi: Any) -> dict[str, Any]:
    if isinstance(poi, dict):
        return poi
    return {
        "id": getattr(poi, "id", getattr(poi, "name", "")),
        "name": getattr(poi, "name", ""),
        "tags": getattr(poi, "tags", []) or [],
        "zone": getattr(poi, "zone", ""),
        "x": getattr(poi, "x", 0),
        "y": getattr(poi, "y", 0),
    }


def _find_poi_object(pois: list[Any], match: dict[str, Any]) -> Any | None:
    mid = str(match.get("id") or "")
    mname = match.get("name")
    for poi in pois:
        pd = _poi_dict(poi)
        if mid and str(pd.get("id")) == mid:
            return poi
        if mname and pd.get("name") == mname:
            return poi
    return None


def match_goal_to_poi(goal: str, pois: list[Any], world: Any = None) -> dict[str, Any] | None:
    if not goal or not pois:
        return None
    goal_lower = goal.lower().strip()
    if goal_lower in POI_ALIASES:
        goal_lower = POI_ALIASES[goal_lower]
    goal_words = set(goal_lower.split())
    best_match: dict[str, Any] | None = None
    best_score = 0.0
    for raw in pois:
        poi = _poi_dict(raw)
        score = 0.0
        poi_name = str(poi.get("name") or poi.get("id") or "").lower()
        if poi_name:
            score += _fuzzy_match_ratio(goal_lower, poi_name) * 0.5
        tags = [str(t).lower() for t in (poi.get("tags") or [])]
        for tag in tags:
            score += _fuzzy_match_ratio(goal_lower, tag) * 0.3
            if any(w in tag for w in goal_words if len(w) >= 3):
                score += 0.15
        if score > best_score:
            best_score = score
            best_match = poi
    return best_match if best_score >= 0.4 else None


def resolve_plan_to_poi(
    plan_text: str,
    world: Any,
    *,
    rr_index: int = 0,
    allow_fallback: bool = True,
) -> tuple[Any | None, str | None, str]:
    """Return (poi_object, display_name, match_kind). kind: strict|keyword|fallback|none."""
    pois = getattr(world, "pois", []) or []
    if not pois:
        return None, None, "none"

    goals = extract_concrete_goals(plan_text or "")
    matched_pairs: list[tuple[str, dict[str, Any]]] = []
    for goal in goals:
        match = match_goal_to_poi(goal, pois, world)
        if match:
            matched_pairs.append((goal, match))

    if not matched_pairs and allow_fallback:
        for token in _keywords_from_text(plan_text, limit=10):
            candidates = [token]
            if token in POI_ALIASES:
                candidates.append(POI_ALIASES[token])
            for cand in candidates:
                match = match_goal_to_poi(cand, pois, world)
                if match:
                    matched_pairs.append((cand, match))
                    break

    if matched_pairs:
        goal, match = matched_pairs[rr_index % len(matched_pairs)]
        poi_obj = _find_poi_object(pois, match)
        name = str(match.get("name") or match.get("id") or goal)
        kind = "strict" if goal in goals else "keyword"
        return poi_obj, name, kind

    if allow_fallback:
        poi = pois[rr_index % len(pois)]
        pd = _poi_dict(poi)
        name = str(pd.get("name") or pd.get("id") or "poi")
        return poi, name, "fallback"

    return None, None, "none"


def _store_concrete_goal(agent: Any, poi: Any) -> None:
    pd = _poi_dict(poi)
    if hasattr(agent, "target_poi"):
        agent.target_poi = poi
    extra = getattr(agent, "extra", None)
    if isinstance(extra, dict):
        extra["stanford_plan_poi"] = poi
        extra["concrete_goal_poi"] = {
            "source": "plan",
            "id": pd.get("id"),
            "name": pd.get("name"),
        }


def apply_plan_to_agent(
    agent: Any,
    plan_text: str,
    world: Any,
    *,
    rr_index: int = 0,
    allow_fallback: bool = True,
) -> str | None:
    """Set agent target POI from plan text. Returns matched POI name or None."""
    poi, name, kind = resolve_plan_to_poi(
        plan_text, world, rr_index=rr_index, allow_fallback=allow_fallback
    )
    if poi is None or kind == "none":
        return None
    _store_concrete_goal(agent, poi)
    return name
