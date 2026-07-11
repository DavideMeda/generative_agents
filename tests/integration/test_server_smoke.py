"""
Server smoke test — verifies FastAPI app starts and responds correctly.
Uses TestClient (no actual network or LLM).
"""
from __future__ import annotations

import pytest

try:
    from fastapi.testclient import TestClient

    from server.main import app
    CLIENT_AVAILABLE = True
except Exception:
    CLIENT_AVAILABLE = False


@pytest.mark.skipif(not CLIENT_AVAILABLE, reason="FastAPI server not importable")
class TestServerSmoke:
    def test_health_endpoint(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_state_before_start(self):
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data

    def test_neat_status_before_start(self):
        client = TestClient(app)
        response = client.get("/api/neat/status")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
