"""
DialogueEngine — generates agent-to-agent conversations.

Accepts an LLM callable and a memory store, returns structured utterances.
Completely decoupled from Stanford internals; works with any LLM backend.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from gen_agent.dialogue.quality import score_utterance
from gen_agent.interfaces.memory_protocol import MemoryProtocol, MemoryQuery

logger = logging.getLogger(__name__)

# Type alias for any callable that takes a string prompt and returns a string.
LLMCallable = Callable[[str], str]


@dataclass
class Utterance:
    speaker_id: str
    speaker_name: str
    text: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Conversation:
    participants: List[str]
    utterances: List[Utterance] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add(self, utterance: Utterance) -> None:
        self.utterances.append(utterance)

    def transcript(self) -> str:
        return "\n".join(
            f"{u.speaker_name}: {u.text}" for u in self.utterances
        )


def _build_prompt(
    speaker_name: str,
    listener_name: str,
    memory_snippets: List[str],
    context: str,
    history: str,
) -> str:
    memories = "\n".join(f"- {m}" for m in memory_snippets) or "None"
    return (
        f"You are {speaker_name}. You are talking with {listener_name}.\n"
        f"Your recent memories:\n{memories}\n\n"
        f"Context: {context}\n\n"
        f"Conversation so far:\n{history}\n\n"
        f"{speaker_name}: "
    )


class DialogueEngine:
    """
    Orchestrates a back-and-forth conversation between two agents.

    Parameters
    ----------
    llm:
        Any callable that takes a string prompt and returns a string response.
        Pass ``None`` to run in stub mode (returns placeholder text).
    memory_store:
        A MemoryProtocol-compliant store used to pull context for each speaker.
    max_turns:
        Maximum number of utterances per conversation.
    """

    def __init__(
        self,
        llm: Optional[LLMCallable] = None,
        memory_store: Optional[MemoryProtocol] = None,
        max_turns: int = 6,
    ) -> None:
        self._llm = llm
        self._memory = memory_store
        self._max_turns = max_turns

    def run(
        self,
        agent_a_id: str,
        agent_a_name: str,
        agent_b_id: str,
        agent_b_name: str,
        context: str = "",
    ) -> Conversation:
        """Run a full conversation. Returns a Conversation object."""
        conversation = Conversation(participants=[agent_a_id, agent_b_id])

        speakers = [
            (agent_a_id, agent_a_name, agent_b_name),
            (agent_b_id, agent_b_name, agent_a_name),
        ]

        history_texts: List[str] = []
        for turn in range(self._max_turns):
            speaker_id, speaker_name, listener_name = speakers[turn % 2]
            memories = self._fetch_memories(speaker_id, context)
            history = conversation.transcript()

            text = self._generate(
                speaker_name=speaker_name,
                listener_name=listener_name,
                memories=memories,
                context=context,
                history=history,
                history_list=history_texts,
            )
            history_texts.append(text)
            conversation.add(
                Utterance(speaker_id=speaker_id, speaker_name=speaker_name, text=text)
            )
            logger.debug("Turn %d — %s: %s", turn + 1, speaker_name, text[:60])

        return conversation

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_memories(self, agent_id: str, query_text: str) -> List[str]:
        if self._memory is None:
            return []
        try:
            records = self._memory.retrieve(
                MemoryQuery(agent_id=agent_id, query_text=query_text, top_k=5)
            )
            return [r.content for r in records]
        except Exception as exc:
            logger.warning("Memory fetch failed for %s: %s", agent_id, exc)
            return []

    def _generate(
        self,
        speaker_name: str,
        listener_name: str,
        memories: List[str],
        context: str,
        history: str,
        history_list: Optional[List[str]] = None,
    ) -> str:
        if self._llm is None:
            return f"{speaker_name} acknowledges what {listener_name} just said and continues the conversation."
        prompt = _build_prompt(speaker_name, listener_name, memories, context, history)
        best_text = ""
        best_score = 0.0
        for _attempt in range(3):  # max 3 retries for quality
            try:
                text = self._llm(prompt).strip()
            except Exception as exc:
                logger.error("LLM call failed: %s", exc)
                return "[LLM error]"
            score = score_utterance(text, history_list or [])
            if score > best_score:
                best_score = score
                best_text = text
            if score >= 0.5:
                break
        return best_text or f"{speaker_name} nods thoughtfully."
