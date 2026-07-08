"""
FastAPI router — REST endpoints and WebSocket for the Gen_Agent server.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from server.state_store import StateStore
from server.tick_runner import register_ws, unregister_ws

logger = logging.getLogger(__name__)
router = APIRouter()


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------

class StartRequest(BaseModel):
    scenario: str = "default"
    agent_names: Optional[List[str]] = None
    ticks: Optional[int] = None
    llm_provider: Optional[str] = None


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


# ------------------------------------------------------------------
# Simulation control
# ------------------------------------------------------------------

@router.get("/api/state")
def get_state() -> Dict[str, Any]:
    store = StateStore.get()
    if store.engine is None:
        return {"running": False, "tick": 0, "agents": {}}
    snap = store.engine.snapshot()
    return {
        "running": store.running,
        "tick": snap.get("tick", 0),
        "agents": snap.get("agents", {}),
        "stats": store.engine.stats(),
    }


@router.post("/api/run/start")
def run_start(req: StartRequest) -> Dict[str, Any]:
    """Build and start a simulation from a named scenario."""
    store = StateStore.get()
    if store.running:
        return {"status": "already running", "tick": store.engine.snapshot()["tick"] if store.engine else 0}

    try:
        from config.scenario import load_scenario
        scenario = load_scenario(req.scenario)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot load scenario '{req.scenario}': {exc}") from exc

    # Override agent names if provided
    if req.agent_names:
        scenario.agent_names = req.agent_names

    # Override LLM provider if provided
    if req.llm_provider:
        import os
        os.environ["LLM_PROVIDER"] = req.llm_provider

    engine = scenario.build_engine()
    store.engine = engine
    store.running = True
    logger.info("Simulation started: scenario=%s agents=%s", req.scenario, scenario.agent_names)
    return {"status": "started", "scenario": req.scenario, "agents": scenario.agent_names}


@router.post("/api/run/pause")
def run_pause() -> Dict[str, str]:
    store = StateStore.get()
    store.running = False
    return {"status": "paused"}


@router.post("/api/run/resume")
def run_resume() -> Dict[str, str]:
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=400, detail="No engine loaded. Call /api/run/start first.")
    store.running = True
    return {"status": "resumed"}


@router.post("/api/run/stop")
def run_stop() -> Dict[str, str]:
    store = StateStore.get()
    store.running = False
    store.engine = None
    return {"status": "stopped"}


# ------------------------------------------------------------------
# Agent info
# ------------------------------------------------------------------

@router.get("/api/agent/{agent_id}/memories")
def agent_memories(agent_id: str, limit: int = 20) -> Dict[str, Any]:
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=404, detail="No simulation running")
    memory = getattr(store.engine, "_memory", None)
    if memory is None:
        return {"agent_id": agent_id, "memories": []}
    from gen_agent.interfaces.memory_protocol import MemoryQuery
    records = memory.retrieve(MemoryQuery(agent_id=agent_id, query_text="", top_k=limit))
    return {
        "agent_id": agent_id,
        "count": len(records),
        "memories": [
            {"content": r.content, "type": r.memory_type, "importance": r.importance}
            for r in records
        ],
    }


@router.get("/api/agent/{agent_id}/state")
def agent_state(agent_id: str) -> Dict[str, Any]:
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=404, detail="No simulation running")
    snap = store.engine.snapshot()
    agents = snap.get("agents", {})
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {"agent_id": agent_id, **agents[agent_id]}


# ------------------------------------------------------------------
# WebSocket
# ------------------------------------------------------------------

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    register_ws(queue)
    logger.info("WebSocket client connected")
    try:
        while True:
            msg = await asyncio.wait_for(queue.get(), timeout=30.0)
            await websocket.send_text(msg)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        unregister_ws(queue)
        logger.info("WebSocket client disconnected")
