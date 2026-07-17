# Web UI — Live Dashboard

The project ships a real-time WebSocket dashboard at `web/index.html`,
served automatically by the FastAPI server.

## Start the server

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in your browser.

## What you see

```
┌─────────────────────────────────┬──────────────────────┐
│  Gen_Agent — Live Dashboard  ●  │  Tick: 12 / running  │
├─────────────────────────────────┤                      │
│                                 │  Agents      5       │
│    2D canvas                    │  Interactions 3      │
│    (agent dots + POI labels)    │  Dialogues   2       │
│                                 │  Memories   48       │
├─────────────────────────────────┴──────────────────────┤
│  [Start]  [Pause]  [Stop]    Scenario: blocking_100    │
├────────────────────────────────────────────────────────┤
│  Event log                                             │
│  tick 10  Giovanni & Elena  2 turns                    │
│  tick 10  Elena arrived at School                      │
└────────────────────────────────────────────────────────┘
```

- **2D canvas**: each coloured dot is an agent; POI names are overlaid on the map
- **Stats panel**: tick counter, interactions, dialogues, memory count
- **Controls**: Start / Pause / Stop the simulation
- **Event log**: scrolling feed of interactions, missions, and dialogue events

## Docker

```bash
docker compose up
# Open http://localhost:8000
```

See [DOCKER.md](DOCKER.md) for production TLS and PostgreSQL setup.

## WebSocket protocol

The server pushes JSON frames on every tick:

```json
{
  "type": "tick",
  "tick": 12,
  "agents": [
    {"id": "a1", "name": "Marco", "x": 8.3, "y": 5.1},
    {"id": "a2", "name": "Lucia", "x": 4.7, "y": 9.2}
  ],
  "events": [
    {"type": "interaction", "agent_names": ["Marco", "Lucia"], "tick": 12}
  ],
  "stats": {"interactions": 3, "dialogues": 2, "memories": 48}
}
```

Full message schema: [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md)

## Customise the UI

The dashboard is a single self-contained HTML file (`web/index.html`).
Common modifications:

- **Canvas colours**: edit the CSS variables in `:root { --accent: ... }`
- **Agent labels**: in the `drawAgents()` function, add `ctx.fillText(agent.name, x, y)`
- **POI boundaries**: draw circles at POI coordinates in `drawWorld()`
- **Dialogue transcript**: subscribe to `event.type === "interaction"` frames

<!-- TODO: add dashboard.gif screenshot here -->
