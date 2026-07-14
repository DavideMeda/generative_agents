# Observability — structlog

Gen_Agent uses [structlog](https://www.structlog.org/) for structured logging.
Central configuration: `server/main.py::_configure_logging()`.

## Log formats

**Dev mode (default)**  
Readable colored console. Active when `LOG_FORMAT` is unset or `dev`.
```
2026-07-10T14:00:00.123456Z [info     ] engine.tick_advanced           tick=42 events=3
2026-07-10T14:00:00.125Z    [warning  ] engine.dialogue_timeout        elapsed_s=30.5 agent_a=Alice agent_b=Bob tick=42
```

**Prod mode (JSON / ndjson)**  
One JSON object per line. Active with `LOG_FORMAT=json`. Compatible with Loki, CloudWatch, Datadog, ELK.
```json
{"event": "engine.tick_advanced", "tick": 42, "events": 3, "level": "debug", "timestamp": "2026-07-10T14:00:00Z"}
{"event": "tick_runner.error", "level": "error", "timestamp": "..."}
```

## Environment variables

| Variable    | Default | Values                | Description              |
|-------------|---------|-----------------------|--------------------------|
| `LOG_LEVEL` | `INFO`  | DEBUG, INFO, WARNING, ERROR | Minimum log level |
| `LOG_FORMAT`| `dev`   | `dev`, `json`         | Output format            |

## Context fields (examples)
- `tick`, `events`: simulation loop progress
- `agent_id`, `agent_names`: actors involved
- `elapsed_s`, `timeout_s`: timing data
- `ws_clients`: connected WebSocket clients

## Usage tips
- For production, prefer `LOG_FORMAT=json` and ship ndjson to your log aggregator.
- Keep `LOG_LEVEL=INFO` in prod; raise to DEBUG only for short debugging sessions.
- To add context to logs, bind fields via `logger.bind(key=value)` before emitting.
