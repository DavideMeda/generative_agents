# Performance Baseline — Gen_Agent

Questo documento riporta le soglie di riferimento per le suite di benchmark.  
I benchmark si trovano in `benchmarks/` e producono JSON in `output/benchmarks/`.

## Come eseguire i benchmark

```bash
# dalla root del progetto
python benchmarks/100_tick_baseline.py
python benchmarks/agent_scaling_profile.py
python benchmarks/dialogue_throughput.py
python benchmarks/memory_retrieval_benchmark.py
```

Ogni script salva automaticamente un file JSON con timestamp in `output/benchmarks/`.

---

## Baseline di riferimento (commit iniziale, hardware: laptop consumer, CPU i5/Ryzen5)

### 1. 100-tick baseline (3 agenti, stub LLM)

| Metrica         | Baseline  | Soglia critica |
|-----------------|-----------|----------------|
| Tempo totale    | < 0.5 s   | > 5 s          |
| ms/tick         | < 5 ms    | > 50 ms        |
| Tick/sec        | > 200     | < 20           |

### 2. Agent scaling profile (20 tick per configurazione)

| N agenti | ms/tick attesi | Soglia critica |
|----------|---------------|----------------|
| 1        | < 1 ms        | > 10 ms        |
| 10       | < 5 ms        | > 50 ms        |
| 50       | < 30 ms       | > 300 ms       |

La complessità per tick è O(n²) nel worst case (pairwise proximity).  
Con `interaction_every_ticks > 1` si può ridurre significativamente.

### 3. Dialogue throughput (4 agenti, stub LLM, 50 tick)

| Metrica               | Baseline  | Note                       |
|-----------------------|-----------|----------------------------|
| Tempo totale          | < 2 s     | Con LLM reale: molto più lento |
| Tick/sec              | > 25      | Stub: nessuna latenza LLM  |

### 4. Memory retrieval (SQLite backend)

| Corpus memorie | ms/query attesi | Soglia critica |
|----------------|-----------------|----------------|
| 10             | < 1 ms          | > 10 ms        |
| 100            | < 3 ms          | > 30 ms        |
| 500            | < 10 ms         | > 100 ms       |

---

## Aggiornare la baseline

Dopo modifiche architetturali rilevanti, rieseguire tutti i benchmark su hardware identico
e aggiornare le soglie in questa tabella.  
Includere nel commit anche il file JSON di output come `output/benchmarks/baseline_<date>.json`.

## Interpretazione

I benchmark usano **stub LLM** (nessuna connessione Ollama/OpenAI).  
Con LLM reale, il throughput scende drasticamente a causa della latenza di rete/inferenza.  
Le soglie di questa guida riguardano solo il core engine (movimento, proximity, missioni).
