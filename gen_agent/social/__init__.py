"""
Social intelligence layer — consensus, game theory, social learning.

Activate independently via env vars:
    ENABLE_CONSENSUS=true
    ENABLE_GAME_THEORY=true
    ENABLE_SOCIAL_LEARNING=true
"""
from gen_agent.social.consensus import ConsensusEngine, ConsensusResult, make_consensus_if_enabled
from gen_agent.social.game_theory import (
    GameEngine,
    GameResult,
    make_game_engine_if_enabled,
    pure_nash_equilibria,
)
from gen_agent.social.social_learning import (
    KnowledgeDiffusion,
    make_knowledge_diffusion_if_enabled,
)

__all__ = [
    "ConsensusEngine", "ConsensusResult", "make_consensus_if_enabled",
    "GameEngine", "GameResult", "make_game_engine_if_enabled", "pure_nash_equilibria",
    "KnowledgeDiffusion", "make_knowledge_diffusion_if_enabled",
]
