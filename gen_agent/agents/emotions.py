"""
Agent emotion state model.

Each agent carries a simple affective state with three dimensions:
  - valence  : positive/negative hedonic tone  [-1.0, 1.0]
  - arousal  : energy level, activation         [ 0.0, 1.0]
  - stress   : accumulated pressure              [ 0.0, 1.0]

Emotions decay toward a neutral baseline every tick and are updated
by interactions with other agents.
"""
from __future__ import annotations

from dataclasses import dataclass

_DECAY = 0.95        # per-tick decay factor toward baseline
_BASELINE_VALENCE = 0.0
_BASELINE_AROUSAL = 0.4
_BASELINE_STRESS = 0.1


@dataclass
class EmotionState:
    valence: float = _BASELINE_VALENCE
    arousal: float = _BASELINE_AROUSAL
    stress: float = _BASELINE_STRESS

    def __post_init__(self) -> None:
        self.valence = _clamp(self.valence, -1.0, 1.0)
        self.arousal = _clamp(self.arousal, 0.0, 1.0)
        self.stress = _clamp(self.stress, 0.0, 1.0)

    def decay(self) -> EmotionState:
        """Return a new state decayed one step toward the neutral baseline."""
        return EmotionState(
            valence=_lerp(self.valence, _BASELINE_VALENCE, 1 - _DECAY),
            arousal=_lerp(self.arousal, _BASELINE_AROUSAL, 1 - _DECAY),
            stress=_lerp(self.stress, _BASELINE_STRESS, 1 - _DECAY),
        )

    def to_dict(self) -> dict:
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "stress": round(self.stress, 3),
        }


def update_from_interaction(
    state: EmotionState,
    partner_valence: float,
    outcome: str = "neutral",
) -> EmotionState:
    """
    Update emotion state after an interaction.

    outcome values:
      "positive" — cooperative, friendly exchange
      "negative" — conflict or hostile exchange
      "neutral"  — neutral exchange (default)
    """
    outcome_delta = {"positive": 0.15, "neutral": 0.0, "negative": -0.2}.get(outcome, 0.0)
    contagion = partner_valence * 0.1   # mild emotional contagion

    new_valence = _clamp(state.valence + outcome_delta + contagion, -1.0, 1.0)
    new_arousal = _clamp(state.arousal + 0.05, 0.0, 1.0)   # interactions raise arousal
    stress_delta = 0.05 if outcome == "negative" else -0.02
    new_stress = _clamp(state.stress + stress_delta, 0.0, 1.0)

    return EmotionState(valence=new_valence, arousal=new_arousal, stress=new_stress)


def contagion_step(
    state: EmotionState,
    neighbour_states: list[EmotionState],
    weight: float = 0.05,
) -> EmotionState:
    """
    Spread emotion across nearby agents (emotional contagion).
    Blends this state slightly toward the average of neighbours.
    """
    if not neighbour_states:
        return state
    avg_valence = sum(s.valence for s in neighbour_states) / len(neighbour_states)
    avg_arousal = sum(s.arousal for s in neighbour_states) / len(neighbour_states)
    return EmotionState(
        valence=_lerp(state.valence, avg_valence, weight),
        arousal=_lerp(state.arousal, avg_arousal, weight),
        stress=state.stress,
    )


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t
