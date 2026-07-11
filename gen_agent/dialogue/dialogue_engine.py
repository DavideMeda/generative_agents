"""DialogueEngine — generates agent-to-agent conversations (English only)."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from gen_agent.dialogue.dialogue_guards import (
    build_retry_hint,
    clean_utterance,
    sanitize_memory_for_prompt,
    validate_utterance,
)
from gen_agent.dialogue.intent_pack import build_intent_pack, intent_pack_to_prompt_section
from gen_agent.dialogue.ollama_manager import build_ollama_prompt
from gen_agent.dialogue.quality import score_utterance
from gen_agent.interfaces.memory_protocol import MemoryProtocol, MemoryQuery

logger = logging.getLogger(__name__)

LLMCallable = Callable[[str], str]

DEFAULT_SCENARIO = (
    "A normal day in a small town. Agents walk between parks, cafes, libraries, "
    "and offices. When they meet, they chat naturally about everyday matters."
)


@dataclass
class Utterance:
    speaker_id: str
    speaker_name: str
    text: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Conversation:
    participants: list[str]
    utterances: list[Utterance] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, utterance: Utterance) -> None:
        self.utterances.append(utterance)

    def transcript(self) -> str:
        return "\n".join(f"{u.speaker_name}: {u.text}" for u in self.utterances)



class DialogueEngine:
    def __init__(
        self,
        llm: LLMCallable | None = None,
        memory_store: MemoryProtocol | None = None,
        max_turns: int = 6,
        min_words: int = 25,
        max_attempts: int = 2,
        use_legacy_quality: bool = True,
        scenario_description: str = DEFAULT_SCENARIO,
    ) -> None:
        self._llm = llm
        self._memory = memory_store
        self._max_turns = max_turns
        self._min_words = min_words
        self._max_attempts = max(1, max_attempts)
        self._use_legacy_quality = use_legacy_quality
        self._scenario = scenario_description or DEFAULT_SCENARIO

    def run(
        self,
        agent_a_id: str,
        agent_a_name: str,
        agent_b_id: str,
        agent_b_name: str,
        context: str = "",
        known_names: list[str] | None = None,
        location: str = "town square",
        traits_a: dict[str, float] | None = None,
        traits_b: dict[str, float] | None = None,
        emotions_a: dict[str, float] | None = None,
        emotions_b: dict[str, float] | None = None,
        relationship: dict[str, float] | None = None,
        deadline: float | None = None,
    ) -> Conversation:
        conversation = Conversation(participants=[agent_a_id, agent_b_id])
        names = known_names or [agent_a_name, agent_b_name]
        loc = location
        if context and "location=" in context:
            for part in context.split():
                if part.startswith("location="):
                    loc = part.split("=", 1)[1]

        # Build intent packs once per conversation
        intent_a = build_intent_pack(traits_a, traits_b, relationship, emotions_a)
        intent_b = build_intent_pack(traits_b, traits_a, relationship, emotions_b)
        intent_sections = {
            agent_a_id: intent_pack_to_prompt_section(intent_a, agent_a_name),
            agent_b_id: intent_pack_to_prompt_section(intent_b, agent_b_name),
        }
        speaker_traits = {agent_a_id: traits_a, agent_b_id: traits_b}
        speaker_emotions = {agent_a_id: emotions_a, agent_b_id: emotions_b}

        speakers = [
            (agent_a_id, agent_a_name, agent_b_name),
            (agent_b_id, agent_b_name, agent_a_name),
        ]
        turns = max(1, self._max_turns)
        per_turn_min = max(8, self._min_words // turns)
        history_texts: list[str] = []
        timed_out = False
        for turn in range(turns):
            if deadline is not None and time.perf_counter() >= deadline:
                timed_out = True
                break
            speaker_id, speaker_name, listener_name = speakers[turn % 2]
            memories = self._fetch_memories(speaker_id, loc, scope="social")
            history = conversation.transcript()
            text = self._generate(
                speaker_name=speaker_name,
                listener_name=listener_name,
                memories=memories,
                location=loc,
                history=history,
                history_list=history_texts,
                known_names=names,
                intent_section=intent_sections.get(speaker_id, ""),
                traits=speaker_traits.get(speaker_id),
                emotions=speaker_emotions.get(speaker_id),
                min_words=per_turn_min,
                deadline=deadline,
            )
            history_texts.append(text)
            conversation.add(
                Utterance(speaker_id=speaker_id, speaker_name=speaker_name, text=text)
            )
            logger.debug("Turn %d — %s: %s", turn + 1, speaker_name, text[:60])
        if timed_out:
            conversation.metadata["timed_out"] = True
        return conversation

    def _fetch_memories(self, agent_id: str, query_text: str, scope: str = "social") -> list[str]:
        if self._memory is None:
            return []
        try:
            records = self._memory.retrieve(
                MemoryQuery(agent_id=agent_id, query_text=query_text, top_k=5, scope=scope)
            )
            out: list[str] = []
            for r in records:
                clean = sanitize_memory_for_prompt(r.content)
                if clean:
                    out.append(clean)
            return out
        except Exception as exc:
            logger.warning("Memory fetch failed for %s: %s", agent_id, exc)
            return []

    def _generate(
        self,
        speaker_name: str,
        listener_name: str,
        memories: list[str],
        location: str,
        history: str,
        history_list: list[str] | None = None,
        known_names: list[str] | None = None,
        intent_section: str = "",
        traits: dict[str, float] | None = None,
        emotions: dict[str, float] | None = None,
        min_words: int | None = None,
        deadline: float | None = None,
    ) -> str:
        if self._llm is None:
            return (
                f"Hey {listener_name}, good to see you here at {location}. "
                f"I was just thinking about what we might do this afternoon."
            )
        word_min = min_words if min_words is not None else self._min_words
        retry_hint = ""
        best_text = ""
        best_score = 0.0
        threshold = 0.55 if self._use_legacy_quality else 0.5
        max_attempts = self._max_attempts

        for attempt in range(max_attempts):
            if deadline is not None and time.perf_counter() >= deadline:
                break
            prompt = build_ollama_prompt(
                speaker_name,
                listener_name,
                memories,
                location,
                history,
                self._scenario,
                word_min,
                intent_section=intent_section,
                retry_hint=retry_hint,
                traits=traits,
                emotions=emotions,
            )
            try:
                raw = self._llm(prompt).strip()
            except Exception as exc:
                logger.error("LLM call failed: %s", exc)
                return f"Sorry {listener_name}, I lost my train of thought for a moment."
            text = clean_utterance(raw, speaker_name)
            ok, reason = validate_utterance(
                text,
                speaker_name,
                listener_name,
                word_min,
                known_names,
            )
            score = self._score_text(
                text, history_list or [], speaker_name, listener_name, known_names, word_min
            )
            if not ok:
                score = min(score, 0.2)

            if self._use_legacy_quality:
                from gen_agent.dialogue.quality_legacy import append_quality_trace
                append_quality_trace({
                    "speaker": speaker_name,
                    "listener": listener_name,
                    "attempt": attempt + 1,
                    "score": score,
                    "valid": ok,
                    "reason": reason,
                    "word_count": len(text.split()),
                    "preview": text[:120],
                })

            if score > best_score:
                best_score = score
                best_text = text
            if ok and score >= threshold:
                return text
            retry_hint = build_retry_hint(reason or "low quality", speaker_name, listener_name, word_min)

        if best_text:
            return best_text
        return (
            f"Hey {listener_name}, it's good to run into you near {location}. "
            f"I've had a lot on my mind lately, but I'm glad we can talk for a minute."
        )

    def _score_text(
        self,
        text: str,
        history: list[str],
        speaker_name: str,
        listener_name: str,
        known_names: list[str] | None,
        min_words: int | None = None,
    ) -> float:
        mw = min_words if min_words is not None else self._min_words
        ok, _ = validate_utterance(
            text, speaker_name, listener_name, mw, known_names
        )
        if not ok:
            return 0.1
        if self._use_legacy_quality:
            from gen_agent.dialogue.quality_legacy import score_utterance_legacy
            return score_utterance_legacy(text, history, speaker_name, listener_name, known_names)
        return score_utterance(text, history)
