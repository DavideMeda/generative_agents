# WebSocket Protocol — Gen_Agent

## Endpoint

```
ws://localhost:8000/ws
```

Il server emette messaggi JSON ad ogni tick della simulazione. Il client si connette e riceve aggiornamenti in tempo reale senza bisogno di polling.

---

## Envelope versionato (schema_version "1")

Ogni messaggio ha la seguente struttura:

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
    },
    "stats": {
      "tick": 42,
      "agent_count": 3,
      "dialogues_started": 1
    }
  }
}
```

### Campi dell'envelope

| Campo            | Tipo   | Descrizione                                              |
|------------------|--------|----------------------------------------------------------|
| `schema_version` | string | Versione del protocollo. Attualmente `"1"`.              |
| `type`           | string | Tipo di evento. Attualmente `"tick_result"`.             |
| `tick`           | int    | Numero di tick simulato (0-indexed).                     |
| `timestamp`      | string | ISO-8601 UTC del momento di emissione sul server.        |
| `data`           | object | Payload specifico per `type` (vedi sotto).               |

### Payload `tick_result`

| Campo     | Tipo   | Descrizione                                                       |
|-----------|--------|-------------------------------------------------------------------|
| `events`  | array  | Lista di stringhe descrittive degli eventi avvenuti nel tick.     |
| `agents`  | object | Mappa `agent_id → AgentSnapshot` (posizione, POI, emozione, ...) |
| `stats`   | object | Statistiche aggregate del motore di simulazione.                  |

---

## Versioning e backward compatibility

- La versione `"1"` è la versione stabile corrente.
- I client devono controllare `schema_version` e ignorare messaggi con versione sconosciuta.
- Nuovi campi potranno essere aggiunti a `data` in modo non-breaking.
- Cambi breaking incrementeranno la versione (es. `"2"`).

---

## Esempio client JavaScript

```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.schema_version !== "1") return;  // versione non supportata
  if (msg.type === "tick_result") {
    console.log(`Tick ${msg.tick}:`, msg.data.agents);
  }
};
```

## Esempio client Python (websockets)

```python
import asyncio
import json
import websockets

async def watch():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("schema_version") != "1":
                continue
            print(f"Tick {msg['tick']}: {len(msg['data']['agents'])} agents")

asyncio.run(watch())
```

---

## Note implementative

- Il server mantiene un set di code asyncio (`asyncio.Queue`) per ogni client connesso.
- La coda ha `maxsize=50`: messaggi in eccesso vengono scartati (lossy broadcast).
- Il timeout di ricezione lato server è 30s: dopo 30s di silenzio il server chiude la connessione.
- Il codice sorgente dell'envelope è in `server/tick_runner.py::_make_envelope`.
