"""Tests for engine_factory and launch_profile."""
from __future__ import annotations

import os

from config.launch_profile import LaunchProfile, apply_profile_to_env, list_presets, load_profile


class TestLaunchProfile:
    def test_blocking_balanced_preset(self):
        profile = load_profile("blocking_balanced")
        assert profile.preset == "blocking_balanced"
        assert profile.ticks == 100
        assert profile.agents == 5
        assert profile.block_on_dialogue is True
        assert profile.enable_stanford_worker is True

    def test_fast_preset(self):
        profile = load_profile("fast")
        assert profile.ticks == 20
        assert profile.agents == 3
        assert profile.block_on_dialogue is False

    def test_all_canonical_presets_load(self):
        for preset in list_presets():
            profile = load_profile(preset)
            assert isinstance(profile, LaunchProfile)

    def test_apply_profile_sets_env(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        monkeypatch.delenv("ENABLE_STANFORD_WORKER", raising=False)

        profile = load_profile("blocking_balanced")
        apply_profile_to_env(profile)

        assert os.environ.get("LLM_PROVIDER") == "ollama"
        assert os.environ.get("OLLAMA_MODEL") == "llama3.2:3b"
        assert os.environ.get("ENABLE_STANFORD_WORKER") == "1"

    def test_to_dict_roundtrip(self):
        profile = load_profile("blocking_balanced")
        d = profile.to_dict()
        restored = LaunchProfile.from_dict(d)
        assert restored.preset == profile.preset
        assert restored.ticks == profile.ticks
