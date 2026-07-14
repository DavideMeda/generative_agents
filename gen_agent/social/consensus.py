"""
[RESEARCH LAYER] ConsensusEngine — collective decision-making for agent groups.

Status: experimental — not covered by CI tests, excluded from the coverage gate.
Enable: ENABLE_CONSENSUS=true

Supported algorithms:
  majority_vote  — simple majority (most frequent choice wins)
  borda_count    — weighted ranking (1st=n pts, 2nd=n-1 pts, ...)
  delphi_round   — iterative: agents update preferences after seeing group stats

Usage:
    engine = ConsensusEngine(llm_callable=my_llm)
    result = engine.decide(
        agent_ids=["a1","a2","a3"],
        question="Should we move to the park?",
        options=["yes","no","maybe"],
        method="borda_count",
    )
    print(result.winner)  # "yes"

Activated when ENABLE_CONSENSUS=true.
"""
from __future__ import annotations

import logging
import os
import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    winner: str
    votes: dict[str, int]
    method: str
    rounds: int = 1


class ConsensusEngine:
    """
    Multi-method consensus engine.
    If llm is provided, each agent votes via LLM prompt.
    Otherwise, votes are random (useful for testing).
    """

    def __init__(
        self,
        llm: Callable[[str], str] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._llm = llm
        self._rng = rng or random.Random()

    def decide(
        self,
        agent_ids: list[str],
        question: str,
        options: list[str],
        method: str = "majority_vote",
        max_delphi_rounds: int = 3,
    ) -> ConsensusResult:
        if method == "majority_vote":
            votes = self._collect_votes(agent_ids, question, options)
            return self._majority(votes, method)
        if method == "borda_count":
            rankings = self._collect_rankings(agent_ids, question, options)
            return self._borda(rankings, method)
        if method == "delphi_round":
            return self._delphi(agent_ids, question, options, max_delphi_rounds)
        raise ValueError(f"Unknown consensus method: {method}")

    # ------------------------------------------------------------------
    # Vote collection
    # ------------------------------------------------------------------

    def _collect_votes(
        self, agent_ids: list[str], question: str, options: list[str]
    ) -> list[str]:
        votes = []
        for agent_id in agent_ids:
            vote = self._get_vote(agent_id, question, options)
            votes.append(vote)
        return votes

    def _collect_rankings(
        self, agent_ids: list[str], question: str, options: list[str]
    ) -> list[list[str]]:
        rankings = []
        for agent_id in agent_ids:
            shuffled = list(options)
            self._rng.shuffle(shuffled)
            if self._llm:
                # Ask LLM to rank options (parse first word of each line)
                prompt = (
                    f"You are agent {agent_id}. Rank from best to worst (one per line):\n"
                    + "\n".join(options)
                    + f"\n\nQuestion: {question}"
                )
                try:
                    resp = self._llm(prompt)
                    parsed = [
                        o for line in resp.splitlines()
                        for o in options
                        if o.lower() in line.lower()
                    ]
                    seen, unique = set(), []
                    for o in parsed:
                        if o not in seen:
                            seen.add(o)
                            unique.append(o)
                    for o in options:
                        if o not in seen:
                            unique.append(o)
                    shuffled = unique
                except Exception:
                    pass
            rankings.append(shuffled)
        return rankings

    def _get_vote(self, agent_id: str, question: str, options: list[str]) -> str:
        if self._llm is None:
            return self._rng.choice(options)
        prompt = (
            f"You are agent {agent_id}. Answer with one of: {', '.join(options)}.\n"
            f"Question: {question}"
        )
        try:
            resp = self._llm(prompt).strip().lower()
            for opt in options:
                if opt.lower() in resp:
                    return opt
        except Exception:
            pass
        return self._rng.choice(options)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _majority(self, votes: list[str], method: str) -> ConsensusResult:
        counts = Counter(votes)
        winner = counts.most_common(1)[0][0]
        return ConsensusResult(winner=winner, votes=dict(counts), method=method)

    def _borda(self, rankings: list[list[str]], method: str) -> ConsensusResult:
        n = len(rankings[0]) if rankings else 1
        scores: dict[str, int] = {}
        for ranking in rankings:
            for i, opt in enumerate(ranking):
                scores[opt] = scores.get(opt, 0) + (n - i)
        winner = max(scores, key=lambda k: scores[k])
        return ConsensusResult(winner=winner, votes=scores, method=method)

    def _delphi(
        self, agent_ids: list[str], question: str, options: list[str], max_rounds: int
    ) -> ConsensusResult:
        current_votes = self._collect_votes(agent_ids, question, options)
        for round_n in range(1, max_rounds + 1):
            counts = Counter(current_votes)
            top = counts.most_common(1)[0][0]
            # Check convergence: if >50% agree, stop
            if counts[top] / len(agent_ids) > 0.5:
                return ConsensusResult(
                    winner=top, votes=dict(counts), method="delphi_round", rounds=round_n
                )
            # Next round: informed vote with knowledge of current stats
            current_votes = self._collect_votes(
                agent_ids,
                f"{question} [current leader: {top} with {counts[top]} votes]",
                options,
            )
        counts = Counter(current_votes)
        winner = counts.most_common(1)[0][0]
        return ConsensusResult(winner=winner, votes=dict(counts), method="delphi_round", rounds=max_rounds)


def make_consensus_if_enabled(llm: Any = None) -> ConsensusEngine | None:
    if os.getenv("ENABLE_CONSENSUS", "false").lower() in ("1", "true", "yes"):
        return ConsensusEngine(llm=llm)
    return None
