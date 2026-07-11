"""
Cognitive Biases Layer — lightweight algebra-only implementations.

Four biases usable as optional hooks inside SimEngine._run_interaction():

- RecencyBias          — memoria recente pesa di più (decay esponenziale)
- AnchoringBias        — la prima stima osservata funge da ancora
- AvailabilityHeuristic— frequenza nella memoria recente → probabilità stimata
- ConfirmationBias     — recupero preferisce memorie con overlap keyword

Enable via  ENABLE_BIASES=true  (gestito in config/engine_factory.py).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ── RecencyBias ──────────────────────────────────────────────────────────────

class RecencyBias:
    """
    Peso moltiplicativo decrescente per età della memoria.

    w = exp(-lambda * age_ticks)

    Se age_ticks=0 → w=1.0; a 5 tick con lambda=0.2 → w≈0.37.
    Usato per pesare quanto una memoria recente influenza la willingness.
    """

    def __init__(self, decay_lambda: float = 0.2) -> None:
        self._lambda = decay_lambda

    def weight(self, age_ticks: int) -> float:
        return math.exp(-self._lambda * max(age_ticks, 0))

    def apply_to_memories(self, memories: list[dict[str, Any]], current_tick: int) -> list[dict[str, Any]]:
        """Aggiunge campo 'recency_weight' a ciascuna memoria."""
        for m in memories:
            age = current_tick - m.get("tick", current_tick)
            m["recency_weight"] = self.weight(age)
        return memories


# ── AnchoringBias ────────────────────────────────────────────────────────────

class AnchoringBias:
    """
    Prima stima osservata per un agente diventa ancora.
    Deviazioni successive vengono attenuate di anchor_weight.

    bias_value = anchor + anchor_weight * (new_value - anchor)
    """

    def __init__(self, anchor_weight: float = 0.3) -> None:
        self._anchor_weight = anchor_weight
        self._anchors: dict[str, float] = {}

    def observe(self, agent_id: str, value: float) -> float:
        """Registra o applica l'ancora per agent_id. Ritorna il valore biased."""
        if agent_id not in self._anchors:
            self._anchors[agent_id] = value
            return value
        anchor = self._anchors[agent_id]
        return anchor + self._anchor_weight * (value - anchor)

    def reset(self, agent_id: str) -> None:
        self._anchors.pop(agent_id, None)


# ── AvailabilityHeuristic ────────────────────────────────────────────────────

class AvailabilityHeuristic:
    """
    Frequenza di un tipo di evento nella memoria recente → probabilità stimata.

    P_biased(event_type) = count(event_type in recent) / len(recent)
    Restituisce 0.0 se il tipo non è mai apparso.

    ponytail: scan lineare O(n), accettabile per window_size <= 100.
    """

    def __init__(self, window_size: int = 20) -> None:
        self._window: list[str] = []
        self._window_size = window_size

    def record(self, event_type: str) -> None:
        self._window.append(event_type)
        if len(self._window) > self._window_size:
            self._window.pop(0)

    def estimated_probability(self, event_type: str) -> float:
        if not self._window:
            return 0.0
        return self._window.count(event_type) / len(self._window)


# ── ConfirmationBias ─────────────────────────────────────────────────────────

class ConfirmationBias:
    """
    Retrieval preferisce memorie con overlap keyword > threshold rispetto al belief corrente.

    overlap = |words(belief) ∩ words(memory)| / |words(belief)|

    Se overlap >= threshold la memoria viene tenuta, altrimenti scartata
    (a meno che non ci siano memorie sopra threshold, nel qual caso ritorna tutte).
    """

    def __init__(self, threshold: float = 0.2) -> None:
        self._threshold = threshold

    @staticmethod
    def _words(text: str) -> set[str]:
        return {w.lower().strip(".,!?;:\"'") for w in text.split() if len(w) > 2}

    def filter(self, belief: str, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filtra le memorie per overlap con il belief corrente."""
        belief_words = self._words(belief)
        if not belief_words:
            return memories
        confirmed = [
            m for m in memories
            if len(belief_words & self._words(m.get("content", ""))) / len(belief_words) >= self._threshold
        ]
        return confirmed if confirmed else memories


# ── BiasLayer — facade opzionale ─────────────────────────────────────────────

@dataclass
class BiasLayer:
    """
    Facade che raggruppa tutti i bias.
    Iniettata in SimEngine come parametro opzionale, non rompe niente se assente.

    Uso in SimEngine._run_interaction():
        if self._biases:
            willingness *= self._biases.willingness_modifier(agent_id, current_tick, recent_events)
    """

    recency: RecencyBias = field(default_factory=RecencyBias)
    anchoring: AnchoringBias = field(default_factory=AnchoringBias)
    availability: AvailabilityHeuristic = field(default_factory=AvailabilityHeuristic)
    confirmation: ConfirmationBias = field(default_factory=ConfirmationBias)

    def willingness_modifier(
        self,
        agent_id: str,
        current_tick: int,
        last_interaction_tick: int | None,
        recent_events: list[str] | None = None,
    ) -> float:
        """
        Combina i bias in un moltiplicatore di willingness [0.1 … 2.0].

        - RecencyBias abbassa la willingness se l'ultima interazione è recente.
        - AvailabilityHeuristic aumenta se 'dialogue' è frequente nella memoria recente.
        - AnchoringBias stabilizza il moltiplicatore verso il valore storico dell'agente.
        """
        age = (current_tick - last_interaction_tick) if last_interaction_tick is not None else 10
        recency_w = self.recency.weight(age)

        avail_boost = 1.0 + self.availability.estimated_probability("dialogue")

        raw = recency_w * avail_boost
        biased = self.anchoring.observe(agent_id, raw)

        # registra l'evento per il prossimo ciclo
        if recent_events:
            for ev in recent_events:
                self.availability.record(ev)

        return max(0.1, min(biased, 2.0))
