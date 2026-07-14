# WebSocket Protocol — Gen_Agent

## Endpoint
```
ws://localhost:8000/ws
```
The server emits a JSON message on every simulation tick; the client receives live updates without polling.

## Versioned envelope (schema_version "1")
```json
{
  "schema_version": "1",
  "type": "tick_result",
  "tick": 42,
  "timestamp": "2026-07-10T14:00:00.123456Z",
  "data": {
    "events": ["Alice moved to Cafe", "Bob started conversation"],
    "agents": {
      "alice": {
        "name": "Alice",
        "position": [3.0, 5.0],
        "target_poi": "Cafe",
        "emotion": "happy"
      }
    }
  }
}
```

### Fields
- `schema_version`: protocol version (string)
- `type`: `"tick_result"` (reserved for future types)
- `tick`: current tick number
- `timestamp`: ISO8601 UTC
- `data.events`: list of event strings
- `data.agents`: per-agent state (id → payload)

Agent payload (example keys):
- `name`: display name
- `position`: `[x, y]`
- `target_poi`: POI name if any
- `traits`: personality traits
- `neat`: latest NEAT action if enabled
- `dialogue`: optional transcript preview (if dialogue occurred)

## Client example (JavaScript)
```js
const ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.schema_version !== "1") return;
  console.log("Tick", msg.tick, "events", msg.data.events);
};
```

## Notes
- Envelope is append-only; prefer adding fields over changing existing ones.
- If you need to bump the schema, increase `schema_version` and keep a compatibility shim client-side.
