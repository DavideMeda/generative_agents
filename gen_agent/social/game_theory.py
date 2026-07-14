"""
[RESEARCH LAYER] GameEngine — strategic interaction modelling via game theory.

Status: experimental — not covered by CI tests, excluded from the coverage gate.
Enable: ENABLE_GAME_THEORY=true

Implemented games:
  prisoner_dilemma — classic cooperate/defect matrix
  stag_hunt        — coordination game (cooperate together or hunt solo)

Nash equilibrium solver for 2×2 payoff matrices (pure strategy only).
The outcome feeds into RLIF to update agent reward signals.
"""
from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Payoff matrices: (row_player_payoff, col_player_payoff)
# Actions: 0=cooperate, 1=defect
PRISONER_DILEMMA: list[list[tuple[float, float]]] = [
    [(3.0, 3.0), (0.0, 5.0)],   # cooperate vs cooperate | cooperate vs defect
    [(5.0, 0.0), (1.0, 1.0)],   # defect vs cooperate   | defect vs defect
]

STAG_HUNT: list[list[tuple[float, float]]] = [
    [(4.0, 4.0), (0.0, 3.0)],
    [(3.0, 0.0), (2.0, 2.0)],
]

_GAMES = {"prisoner_dilemma": PRISONER_DILEMMA, "stag_hunt": STAG_HUNT}


@dataclass
class GameResult:
    game: str
    action_a: str
    action_b: str
    payoff_a: float
    payoff_b: float
    outcome: str   # "positive" | "neutral" | "negative" — for RLIF


def pure_nash_equilibria(matrix: list[list[tuple[float, float]]]) -> list[tuple[int, int]]:
    """
    Find all pure strategy Nash Equilibria in a 2×2 payoff matrix.
    Returns list of (row_action, col_action) pairs.
    """
    n_rows, n_cols = len(matrix), len(matrix[0])
    equilibria = []
    for r in range(n_rows):
        for c in range(n_cols):
            # Row player: is r the best response to c?
            row_payoffs = [matrix[rr][c][0] for rr in range(n_rows)]
            if matrix[r][c][0] < max(row_payoffs):
                continue
            # Col player: is c the best response to r?
            col_payoffs = [matrix[r][cc][1] for cc in range(n_cols)]
            if matrix[r][c][1] < max(col_payoffs):
                continue
            equilibria.append((r, c))
    return equilibria


class GameEngine:
    """
    Models pairwise strategic interactions between agents.
    Agents choose actions randomly (future: driven by traits via RLIF).
    """

    _ACTION_NAMES = {0: "cooperate", 1: "defect"}

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        logger.info("GameEngine active")

    def play(
        self,
        id_a: str,
        id_b: str,
        game: str = "prisoner_dilemma",
        traits_a: dict[str, float] | None = None,
        traits_b: dict[str, float] | None = None,
    ) -> GameResult:
        matrix = _GAMES.get(game, PRISONER_DILEMMA)
        action_a = self._choose_action(traits_a)
        action_b = self._choose_action(traits_b)
        payoff_a, payoff_b = matrix[action_a][action_b]

        # Derive RLIF-compatible outcome
        total = payoff_a + payoff_b
        if total >= 6.0:
            outcome = "positive"
        elif total <= 2.0:
            outcome = "negative"
        else:
            outcome = "neutral"

        result = GameResult(
            game=game,
            action_a=self._ACTION_NAMES[action_a],
            action_b=self._ACTION_NAMES[action_b],
            payoff_a=payoff_a,
            payoff_b=payoff_b,
            outcome=outcome,
        )
        logger.debug(
            "GameEngine %s vs %s → %s/%s payoffs=(%.1f, %.1f)",
            id_a, id_b, result.action_a, result.action_b, payoff_a, payoff_b,
        )
        return result

    def _choose_action(self, traits: dict[str, float] | None) -> int:
        """
        Action choice: high agreeableness → more likely to cooperate.
        Without traits, 50/50.
        """
        if traits is None:
            return self._rng.randint(0, 1)
        agr = traits.get("agreeableness", 0.5)
        return 0 if self._rng.random() < agr else 1  # 0=cooperate


def make_game_engine_if_enabled() -> GameEngine | None:
    if os.getenv("ENABLE_GAME_THEORY", "false").lower() in ("1", "true", "yes"):
        return GameEngine()
    return None
