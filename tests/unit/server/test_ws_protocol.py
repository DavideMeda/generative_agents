"""
Test schema WS protocol — M2.

Verifica che ogni messaggio emesso da _make_envelope rispetti
l'envelope versionato documentato in docs/guides/WEBSOCKET_PROTOCOL.md.
"""
from __future__ import annotations

import json

import pytest

from server.tick_runner import WS_SCHEMA_VERSION, _make_envelope, _broadcast, register_ws, unregister_ws
import asyncio


REQUIRED_ENVELOPE_KEYS = {"schema_version", "type", "tick", "timestamp", "data"}
REQUIRED_DATA_KEYS = {"events", "agents", "stats"}


class TestEnvelopeSchema:
    def _sample(self, tick: int = 5) -> dict:
        return _make_envelope(
            "tick_result",
            tick=tick,
            data={"events": ["e1"], "agents": {"a1": {"name": "Alice"}}, "stats": {"tick": tick}},
        )

    def test_envelope_has_all_required_keys(self):
        env = self._sample()
        assert REQUIRED_ENVELOPE_KEYS <= env.keys()

    def test_schema_version_is_correct(self):
        env = self._sample()
        assert env["schema_version"] == WS_SCHEMA_VERSION

    def test_type_is_string(self):
        env = self._sample()
        assert isinstance(env["type"], str)

    def test_tick_matches_input(self):
        env = self._sample(tick=99)
        assert env["tick"] == 99

    def test_timestamp_is_utc_iso(self):
        env = self._sample()
        ts = env["timestamp"]
        assert isinstance(ts, str)
        assert ts.endswith("Z"), f"timestamp deve finire con Z (UTC): {ts}"
        # deve essere parsabile
        from datetime import datetime
        datetime.fromisoformat(ts.rstrip("Z"))

    def test_data_has_required_keys(self):
        env = self._sample()
        assert REQUIRED_DATA_KEYS <= env["data"].keys()

    def test_envelope_is_json_serializable(self):
        env = self._sample()
        raw = json.dumps(env)
        parsed = json.loads(raw)
        assert parsed["schema_version"] == WS_SCHEMA_VERSION

    def test_different_ticks_produce_different_envelopes(self):
        e1 = self._sample(tick=1)
        e2 = self._sample(tick=2)
        assert e1["tick"] != e2["tick"]

    def test_schema_version_constant_is_string(self):
        assert isinstance(WS_SCHEMA_VERSION, str)

    def test_agents_dict_preserved_in_data(self):
        agents = {"alice": {"name": "Alice", "position": [1.0, 2.0]}}
        env = _make_envelope("tick_result", tick=0, data={"events": [], "agents": agents, "stats": {}})
        assert env["data"]["agents"] == agents


class TestBroadcastIntegration:
    """Verifica che _broadcast usi l'envelope e che la coda riceva JSON valido."""

    def test_broadcast_puts_json_string_in_queue(self):
        q: asyncio.Queue = asyncio.Queue(maxsize=10)
        register_ws(q)
        try:
            payload = _make_envelope("tick_result", tick=1, data={"events": [], "agents": {}, "stats": {}})
            _broadcast(payload)
            assert not q.empty()
            raw = q.get_nowait()
            parsed = json.loads(raw)
            assert parsed["schema_version"] == WS_SCHEMA_VERSION
            assert parsed["tick"] == 1
        finally:
            unregister_ws(q)
