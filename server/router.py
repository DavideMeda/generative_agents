"""
FastAPI router — REST endpoints and WebSocket for the Gen_Agent server.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

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
    agent_names: list[str] | None = None
    ticks: int | None = None
    llm_provider: str | None = None


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ------------------------------------------------------------------
# Simulation control
# ------------------------------------------------------------------

@router.get("/api/state")
def get_state() -> dict[str, Any]:
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
def run_start(req: StartRequest) -> dict[str, Any]:
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
    store.extras = getattr(scenario, "_engine_extras", None)
    store.running = True
    logger.info("Simulation started: scenario=%s agents=%s", req.scenario, scenario.agent_names)
    return {"status": "started", "scenario": req.scenario, "agents": scenario.agent_names}


@router.post("/api/run/pause")
def run_pause() -> dict[str, str]:
    store = StateStore.get()
    store.running = False
    return {"status": "paused"}


@router.post("/api/run/resume")
def run_resume() -> dict[str, str]:
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=400, detail="No engine loaded. Call /api/run/start first.")
    store.running = True
    return {"status": "resumed"}


@router.post("/api/run/stop")
def run_stop() -> dict[str, str]:
    store = StateStore.get()
    store.running = False
    store.engine = None
    return {"status": "stopped"}


# ------------------------------------------------------------------
# Agent info
# ------------------------------------------------------------------

@router.get("/api/agent/{agent_id}/memories")
def agent_memories(agent_id: str, limit: int = 20) -> dict[str, Any]:
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
def agent_state(agent_id: str) -> dict[str, Any]:
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=404, detail="No simulation running")
    snap = store.engine.snapshot()
    agents = snap.get("agents", {})
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {"agent_id": agent_id, **agents[agent_id]}


@router.get("/api/neat/status")
def neat_status() -> dict[str, Any]:
    store = StateStore.get()
    mgr = getattr(store.engine, "_neat_manager", None) if store.engine else None
    if mgr is None:
        return {"enabled": False, "available": False}
    return mgr.status()


@router.post("/api/neat/start")
def neat_start() -> dict[str, Any]:
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=400, detail="No simulation running")
    mgr = getattr(store.engine, "_neat_manager", None)
    if mgr is None:
        from server.neat_manager import create_neat_manager
        mgr = create_neat_manager(store.engine)
        store.engine._neat_manager = mgr
    status = mgr.start()
    return mgr.status() if hasattr(mgr, "status") else {"ok": True, "status": str(status)}


@router.post("/api/neat/stop")
def neat_stop() -> dict[str, Any]:
    store = StateStore.get()
    mgr = getattr(store.engine, "_neat_manager", None) if store.engine else None
    if mgr is None:
        return {"ok": False, "error": "neat_not_active"}
    mgr.stop()
    return mgr.status()


class NeatEnableRequest(BaseModel):
    mode: str = "movement"
    agent_id: str | None = None


@router.post("/api/neat/enable")
def neat_enable(req: NeatEnableRequest) -> dict[str, Any]:
    """Enable NEAT policy for all agents or a specific one."""
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=400, detail="No simulation running")
    mgr = getattr(store.engine, "_neat_manager", None)
    if mgr is None:
        from server.neat_manager import create_neat_manager
        mgr = create_neat_manager(store.engine)
        store.engine._neat_manager = mgr
    try:
        # Build simple identity policy if NEAT not trained yet
        if hasattr(mgr, "_trainer") and mgr._trainer is not None:
            best = getattr(mgr._trainer, "best_genome", None)
            if best is not None:
                from gen_agent.training.neat.policy import NeatPolicy
                if req.agent_id:
                    store.engine.set_neat_policy_for_agent(req.agent_id, NeatPolicy(best), req.mode)
                else:
                    store.engine.set_neat_policy_for_all(lambda _: NeatPolicy(best), req.mode)
        mgr.start()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "mode": req.mode, **mgr.status()}


@router.post("/api/neat/disable")
def neat_disable() -> dict[str, Any]:
    """Disable NEAT for all agents."""
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=400, detail="No simulation running")
    store.engine.disable_neat_for_all()
    return {"ok": True, "neat_enabled": False}


class NeatLoadRequest(BaseModel):
    path: str


@router.post("/api/neat/load")
def neat_load(req: NeatLoadRequest) -> dict[str, Any]:
    """Load a saved NEAT genome from disk and apply to all agents."""
    store = StateStore.get()
    if store.engine is None:
        raise HTTPException(status_code=400, detail="No simulation running")
    mgr = getattr(store.engine, "_neat_manager", None)
    if mgr is None:
        from server.neat_manager import create_neat_manager
        mgr = create_neat_manager(store.engine)
        store.engine._neat_manager = mgr
    return mgr.load_best(req.path)


@router.post("/api/neat/continuous/start")
def neat_continuous_start() -> dict[str, Any]:
    store = StateStore.get()
    mgr = getattr(store.engine, "_neat_manager", None) if store.engine else None
    if mgr is None:
        return {"ok": False, "error": "neat_not_active"}
    return mgr.start_continuous()


@router.post("/api/neat/continuous/stop")
def neat_continuous_stop() -> dict[str, Any]:
    store = StateStore.get()
    mgr = getattr(store.engine, "_neat_manager", None) if store.engine else None
    if mgr is None:
        return {"ok": False, "error": "neat_not_active"}
    return mgr.stop_continuous()


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
