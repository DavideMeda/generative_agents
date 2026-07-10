# Observability — Gen_Agent structlog

## Libreria

Gen_Agent usa [structlog](https://www.structlog.org/) per il logging strutturato.  
La configurazione centralizzata è in `server/main.py::_configure_logging()`.

---

## Formato dei log

### Modalità dev (default)

Output colorato e leggibile in console. Attivo quando `LOG_FORMAT` non è impostato o è `dev`.

```
2026-07-10T14:00:00.123456Z [info     ] engine.tick_advanced           tick=42 events=3
2026-07-10T14:00:00.125Z    [warning  ] engine.dialogue_timeout        elapsed_s=30.5 agent_a=Alice agent_b=Bob tick=42
```

### Modalità prod (JSON / ndjson)

Ogni riga è un oggetto JSON. Attivo con `LOG_FORMAT=json`.  
Compatibile con Loki, CloudWatch, Datadog, ELK.

```json
{"event": "engine.tick_advanced", "tick": 42, "events": 3, "level": "debug", "timestamp": "2026-07-10T14:00:00Z"}
{"event": "tick_runner.error", "level": "error", "timestamp": "..."}
```

---

## Variabili d'ambiente

| Variabile    | Default | Valori validi       | Descrizione                    |
|--------------|---------|---------------------|-------------------------------|
| `LOG_LEVEL`  | `INFO`  | DEBUG, INFO, WARNING, ERROR | Livello minimo di log    |
| `LOG_FORMAT` | `dev`   | `dev`, `json`       | Formato output                |

---

## Campi contestuali standard

I moduli core propagano questi campi strutturati:

| Campo        | Modulo           | Descrizione                             |
|--------------|------------------|-----------------------------------------|
| `tick`       | engine, runner   | Numero di tick simulato                 |
| `agent_a/b`  | engine           | Nome degli agenti coinvolti             |
| `elapsed_s`  | engine           | Durata operazione in secondi            |
| `events`     | engine, runner   | Numero di eventi nel tick               |
| `ws_clients` | tick_runner      | Client WebSocket connessi               |
| `interval`   | tick_runner      | Intervallo tick in secondi              |
| `turns`      | engine           | Numero di turni dialogo                 |

---

## Come usare structlog nel codice

```python
import structlog

logger = structlog.get_logger(__name__)

# Log con campi contestuali
logger.info("modulo.evento", agent_id="alice", tick=42, duration_ms=12.5)

# Log di errore
logger.error("modulo.errore", exc_info=exc, context="descrizione")

# Binding context per riuso
log = logger.bind(run_id="run_123", agent_id="alice")
log.debug("memory.stored", content_len=150)
```

---

## Integrazione CI

I log strutturati non interferiscono con pytest (pytest cattura stdout).  
Per test che verificano output di log, usare `caplog` di pytest normalmente.

---

## Upgrade path

- **run_id correlation:** usare `structlog.contextvars.bind_contextvars(run_id=...)` all'avvio di ogni simulazione per correlare tutti i log di una run.
- **Trace distribuito:** integrare OpenTelemetry via `structlog.processors` per collegare ai sistemi di tracing.
