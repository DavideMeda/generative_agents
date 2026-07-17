# Performance Benchmarks

Historical performance data for tracking regressions across commits.

## Add an entry

After running a simulation, add its report to the history:

```bash
python scripts/run_sim_100_ticks_blocking.py --preset blocking_balanced --report output/bench.json
python benchmarks/add_entry.py output/bench.json --notes "after upgrading Ollama model"
```

## View history

```bash
python -c "import json; [print(e['date'], e['commit'], e['llm'], e['dialogues'], 'dialogues', e['real_time_sec'], 's') for e in json.load(open('benchmarks/history.json'))]"
```

## Schema

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO date of the run |
| `commit` | string | Short git commit hash |
| `preset` | string | Simulation preset name |
| `ticks` | int | Number of ticks run |
| `agents` | int | Number of agents |
| `llm` | string | Provider: `ollama`, `openrouter`, `mock` |
| `model` | string | Model name |
| `dialogues` | int | Completed dialogues |
| `utterances` | int | Total LLM utterances |
| `memories` | int | Memories stored at end |
| `reflections` | int | Reflections generated |
| `real_time_sec` | float | Wall-clock time |
| `avg_sec_per_tick` | float | Average time per tick |
| `notes` | string | Optional notes |

## Interpreting results

- **dialogues**: should scale roughly linearly with ticks for a healthy run
- **avg_sec_per_tick**: dominated by LLM latency; mock runs are <0.01 s/tick
- **reflections**: triggered every 5 stored memories (configurable via `REFLECTION_TRIGGER`)
- **Ollama instability**: if `avg_sec_per_tick` >> expected, check `llm_metrics.circuit_state`
  in the report JSON — `OPEN` means the circuit breaker fired due to repeated failures
