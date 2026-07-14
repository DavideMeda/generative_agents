# Performance Baseline

Lightweight benchmarks to gauge engine speed (no networked LLM unless noted).

## Benchmarks

- **100_tick_baseline**: 3 agents, 100 ticks, mock dialogue. Measures total time and ticks/sec.
- **dialogue_throughput**: high interaction frequency, stub LLM. Counts completed dialogues over 50 ticks.
- **agent_scaling_profile**: increases agent count to observe tick time growth.
- **memory_retrieval_benchmark**: retrieval latency with SQLite as memory size grows.

## How to run
```bash
python benchmarks/100_tick_baseline.py
python benchmarks/dialogue_throughput.py
python benchmarks/agent_scaling_profile.py
python benchmarks/memory_retrieval_benchmark.py
```

## Expected ballpark (mock LLM, local dev)
- 100_tick_baseline: low seconds on a modern laptop; ticks/sec >> 10.
- dialogue_throughput: dozens of dialogues in 50 ticks.
- Retrieval benchmark: stays sub-second for small corpora; watch growth as memories increase.

## Notes
- Ollama or remote LLMs will dominate runtime when enabled (blocking dialogues).
- Use `--llm mock` for speed tests; `--llm ollama` only when measuring end-to-end realism.
- Pin hardware/CPU governor when comparing runs to avoid variance.
