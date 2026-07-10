"""
Launch profile — load/save user simulation presets and map to env flags.

Ported slim from Gen_Agent legacy config/launch_profile.py.

Usage:
    from config.launch_profile import load_profile, apply_profile_to_env, CANONICAL_PRESETS
    profile = load_profile("blocking_balanced")
    apply_profile_to_env(profile)
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _CONFIG_DIR.parent

CANONICAL_PRESETS = (
    "fast",
    "blocking_balanced",
    "dense_100",
    "complex",
    "long",
)

# ------------------------------------------------------------------
# Preset definitions
# ------------------------------------------------------------------

_PRESETS: Dict[str, Dict[str, Any]] = {
    "fast": {
        "ticks": 20,
        "agents": 3,
        "block_on_dialogue": False,
        "dialogue_max_turns": 2,
        "interaction_radius": 3.0,
        "min_gap_ticks": 10,
        "enable_stanford_worker": False,
        "enable_neat": False,
        "enable_hrm": False,
        "enable_rlif": False,
        "enable_game_theory": False,
        "mission_duration_ticks": 10,
    },
    "blocking_balanced": {
        "ticks": 100,
        "agents": 5,
        "block_on_dialogue": True,
        "dialogue_max_turns": 3,
        "interaction_radius": 5.0,
        "min_gap_ticks": 32,
        "enable_stanford_worker": True,
        "enable_neat": False,
        "enable_hrm": False,
        "enable_rlif": False,
        "enable_game_theory": True,
        "mission_duration_ticks": 30,
        "dialogue_min_words": 25,
    },
    "dense_100": {
        "ticks": 100,
        "agents": 8,
        "block_on_dialogue": False,
        "dialogue_max_turns": 3,
        "interaction_radius": 4.0,
        "min_gap_ticks": 20,
        "enable_stanford_worker": True,
        "enable_neat": False,
        "enable_hrm": True,
        "enable_rlif": True,
        "enable_game_theory": True,
        "mission_duration_ticks": 25,
    },
    "complex": {
        "ticks": 200,
        "agents": 10,
        "block_on_dialogue": False,
        "dialogue_max_turns": 6,
        "interaction_radius": 6.0,
        "min_gap_ticks": 40,
        "enable_stanford_worker": True,
        "enable_neat": True,
        "enable_hrm": True,
        "enable_rlif": True,
        "enable_game_theory": True,
        "mission_duration_ticks": 40,
    },
    "long": {
        "ticks": 500,
        "agents": 5,
        "block_on_dialogue": True,
        "dialogue_max_turns": 4,
        "interaction_radius": 5.0,
        "min_gap_ticks": 32,
        "enable_stanford_worker": True,
        "enable_neat": False,
        "enable_hrm": False,
        "enable_rlif": False,
        "enable_game_theory": True,
        "mission_duration_ticks": 50,
    },
}


@dataclass
class LaunchProfile:
    preset: str = "blocking_balanced"
    ticks: int = 100
    agents: int = 5
    agent_names: list = field(default_factory=lambda: ["Marco", "Lucia", "Giovanni", "Anna", "Elena"])
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2:3b"
    block_on_dialogue: bool = True
    dialogue_max_turns: int = 4
    interaction_radius: float = 5.0
    min_gap_ticks: int = 32
    mission_duration_ticks: int = 30
    enable_stanford_worker: bool = True
    enable_neat: bool = False
    enable_hrm: bool = False
    enable_rlif: bool = False
    enable_game_theory: bool = True
    enable_social_learning: bool = False
    enable_seal: bool = False
    enable_vector_memory: bool = False
    enable_legacy_dialogue_quality: bool = True
    dialogue_min_words: int = 25
    reflection_trigger: int = 5
    consolidation_interval: int = 50
    ollama_timeout: int = 300
    data_dir: str = "data"
    scenario_description: str = (
        "A normal day in a small town. Agents walk between parks, cafes, libraries, "
        "and offices. When they meet, they chat naturally about everyday matters."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LaunchProfile":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


def load_profile(preset: str = "blocking_balanced") -> LaunchProfile:
    """Load a preset profile, optionally overridden by a user profile JSON file."""
    base = _PRESETS.get(preset, _PRESETS["blocking_balanced"])
    profile = LaunchProfile(preset=preset, **{k: v for k, v in base.items()
                                              if k in LaunchProfile.__dataclass_fields__})

    # Allow user overrides via config/user_simulation_profile.json
    user_path = _CONFIG_DIR / "user_simulation_profile.json"
    if user_path.exists():
        try:
            overrides = json.loads(user_path.read_text(encoding="utf-8"))
            # Apply top-level keys that match LaunchProfile fields
            for k, v in overrides.items():
                if k in LaunchProfile.__dataclass_fields__:
                    setattr(profile, k, v)
        except Exception as exc:
            logger.warning("Could not load user profile: %s", exc)

    return profile


def apply_profile_to_env(profile: LaunchProfile) -> None:
    """Map LaunchProfile fields to environment variables consumed by engine_factory."""
    env = os.environ
    env.setdefault("LLM_PROVIDER", profile.llm_provider)
    env.setdefault("OLLAMA_MODEL", profile.llm_model)
    env.setdefault("OLLAMA_TIMEOUT", str(profile.ollama_timeout))
    env.setdefault("GEN_AGENT_DATA_DIR", profile.data_dir)
    env.setdefault("DIALOGUE_MIN_WORDS", str(profile.dialogue_min_words))
    env.setdefault("DIALOGUE_MAX_ATTEMPTS", "2" if profile.block_on_dialogue else "3")
    env.setdefault("REFLECTION_TRIGGER", str(profile.reflection_trigger))
    env.setdefault("CONSOLIDATION_INTERVAL", str(profile.consolidation_interval))
    env.setdefault("SCENARIO_DESCRIPTION", profile.scenario_description)
    # Feature flags
    _set_flag(env, "ENABLE_STANFORD_WORKER", profile.enable_stanford_worker)
    _set_flag(env, "ENABLE_NEAT", profile.enable_neat)
    _set_flag(env, "ENABLE_HRM", profile.enable_hrm)
    _set_flag(env, "ENABLE_RLIF", profile.enable_rlif)
    _set_flag(env, "ENABLE_GAME_THEORY", profile.enable_game_theory)
    _set_flag(env, "ENABLE_SOCIAL_LEARNING", profile.enable_social_learning)
    _set_flag(env, "ENABLE_SEAL", profile.enable_seal)
    _set_flag(env, "ENABLE_VECTOR_MEMORY", profile.enable_vector_memory)
    _set_flag(env, "ENABLE_LEGACY_DIALOGUE_QUALITY", profile.enable_legacy_dialogue_quality)


def _set_flag(env: Dict[str, str], name: str, value: bool) -> None:
    env.setdefault(name, "1" if value else "0")


def save_profile(profile: LaunchProfile, path: Optional[Path] = None) -> None:
    target = path or (_CONFIG_DIR / "user_simulation_profile.json")
    target.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
    logger.info("Profile saved to %s", target)


def list_presets() -> list:
    return list(_PRESETS.keys())
