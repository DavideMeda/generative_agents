# Confronto definitivo: Nuovo Gen_Agent vs Gen_Agent (legacy)

Documento aggiornato il **2026-07-10** dopo la run definitiva `sim_blocking_100_v2.json` (dialoghi allineati al legacy) e i confronti automatici via `scripts/compare_simulations.py`.

## Verdetto esecutivo

| | Nuovo Gen_Agent | Gen_Agent legacy |
|---|----------------|------------------|
| **Stato** | Progetto attivo (fork di `joonspk-research/generative_agents`) | v2.2.0 archiviato |
| **Parità soglie** | **8/8** (`parity_ok: true`) | Era il riferimento |
| **Run blocking 100 tick** | Completata e documentata | Nessuna run `blocking_balanced` 100 tick comparabile nel repo |
| **Plan→POI** | **24 match** (≥ legacy) | 23 match |
| **Punto di forza** | Architettura, qualità dialoghi, Plan→POI, deploy | Ampiezza ricerca, harness, benchmark, UI |

**Conclusione:** il fork ha **raggiunto e superato la parità funzionale** sul percorso `blocking_balanced` (5 agenti, 100 tick, Ollama blocking): stessi Plan→POI del legacy, più dialoghi e riflessioni attive. Il legacy resta più ampio come piattaforma di ricerca; il nuovo è più snello da mantenere e deployare, ma più lento in modalità blocking.

---

## Fonti dati

| Artefatto | Percorso |
|-----------|----------|
| Run definitiva nuovo | `output/sim_blocking_100_v2.json` |
| Parità qualità | `output/parity_report.json` |
| Confronto vs `dense_100_efficient` | `output/comparison_vs_legacy.json` |
| Legacy `dense_100_efficient` | `../Gen_Agent/outputs/test_simulazioni/run_20260611_163750/report_test_100ticks_20260611_164820.json` |
| Legacy `dense_100` | `../Gen_Agent/outputs/test_simulazioni/run_20260612_111137/report_test_100ticks_20260612_113258.json` |
| Benchmark cross-framework legacy | `../Gen_Agent/docs/manual/benchmark/runs/gap_analysis.md` |

### Parametri run nuovo (`blocking_100`)

- Preset: `blocking_balanced`
- Modello: `llama3.2:3b`
- Agenti: 5 (Marco, Lucia, Giovanni, Anna, Elena)
- `block_on_dialogue: true`, 3 turni/dialogo, timeout 180 s (allineato al legacy)
- `interaction_radius=5`, `every=10`, `min_gap=32`
- Tempo reale: **2937 s (~49 min)**

### Riproducibilità (importante per uso accademico)

| Componente | Deterministico? |
|------------|-----------------|
| Movimento agenti, prossimità, missioni | Sì (`seed=42`) |
| Testo dialoghi, riflessioni, piani LLM | No (Ollama stocastico) |
| Metriche `core_score`, Plan→POI | **Indicative** — non bit-identiche tra run |

Per confronti validi, registrare sempre: commit git, `OLLAMA_MODEL`, preset, numero tick.
I numeri in questo documento provengono da `sim_blocking_100_v2.json` (run del 2026-07-10).

---

## Confronto 1 — Parità qualità (soglie legacy)

Script: `python scripts/compare_simulations.py --report output/sim_blocking_100_v2.json --skip-legacy`

| Check | Valore nuovo | Soglia | Esito |
|-------|--------------|--------|-------|
| core_score mean | **0.898** | ≥ 0.50 | OK |
| meta comments | 0 | == 0 | OK |
| non-English turns | 0 | == 0 | OK |
| wrong addressee | 0 | == 0 | OK |
| reflections/agent/100t | **5.4** | ≥ 1.0 | OK |
| plan-POI matches | **24** | ≥ 1 | OK |
| utterances (norm 100t) | **54** | ≥ 8 | OK |
| per-agent memory DBs | **67** | ≥ agents | OK |

**Risultato: 8/8** — tutte le soglie di accettazione superate.

Metriche chiave della run:

| Metrica | Valore |
|---------|--------|
| Dialoghi / utterances | 18 / 54 |
| Interazioni | 18 |
| Missioni completate | 33 |
| Plan goals extracted / matched | 48 / 24 |
| Concrete goals used (plan) | 8 |
| Memorie totali | 87 |
| Riflessioni | 27 |
| Plan→POI matching rate | 0.50 |

---

## Confronto 2 — Quantitativo vs legacy `dense_100_efficient`

Stesso modello (`llama3.2:3b`), 100 tick, **preset diverso**: nuovo = blocking, legacy = non-blocking efficient.

Script:

```bash
python scripts/compare_simulations.py \
  --report output/sim_blocking_100_v2.json \
  --legacy-report ../Gen_Agent/outputs/test_simulazioni/run_20260611_163750/report_test_100ticks_20260611_164820.json \
  --comparison-out output/comparison_vs_legacy.json
```

| Metrica | Nuovo (blocking) | Legacy (dense_100_efficient) | Note |
|---------|------------------|------------------------------|------|
| Tick | 100 | 100 | |
| Dialoghi | **18** | 13 | Nuovo: più dialoghi |
| Interazioni | **18** | 13 | |
| Plan goals extracted | **48** | 23 | Nuovo estrae di più |
| Plan-POI matches | **24** | 23 | **Parità raggiunta** |
| Concrete goals used | 8 | **18** | Legacy migliore su navigazione plan-driven |
| Missioni completate | **33** | 18 | Nuovo: più missioni |
| Memorie totali | **87** | 4 | Conteggio diverso (persistenza per-agente) |
| Riflessioni | **27** | n/a | Solo nuovo |
| core_score mean | **0.898** | n/a | Solo nuovo (da dialogue_log) |
| Objective completion | n/a | **75%** | Solo legacy harness |
| Tempo (s) | 2937 | **629** | Blocking vs non-blocking |

**Interpretazione:** il nuovo in blocking ha ormai **Plan→POI in parità col legacy** (24 vs 23 match assoluti) con **più dialoghi, più memorie, riflessioni attive e qualità dialoghi misurata**. Il `matching_rate` grezzo è 0.50 solo perché il nuovo estrae molti più goal (48 vs 23); in valore assoluto i match superano il legacy. L'unico vantaggio residuo del legacy è la **velocità** (629 s vs 2937 s, perché non-blocking) e l'uso più frequente dei goal concreti nella navigazione (18 vs 8).

---

## Confronto 3 — Quantitativo vs legacy `dense_100` (dialoghi intensivi)

Legacy con più interazioni per tick (non-blocking, `min_gap` più basso).

| Metrica | Nuovo (blocking) | Legacy (dense_100) |
|---------|------------------|---------------------|
| Dialoghi | 16 | **57** |
| Interazioni | 16 | **57** |
| Plan-POI matches | 3 | 0 |
| Tempo (s) | 4271 | 1280 |
| Objective completion | n/a | 50% |

Il preset `dense_100` legacy massimizza i dialoghi ma **non attiva Plan→POI** in quella run (0 match). Confronto utile per volume dialoghi, non per parità blocking.

---

## Matrice architettura

| Aspetto | Legacy | Nuovo |
|---------|--------|-------|
| Core | `core/` ~337 moduli | `gen_agent/` ~73 file |
| Wiring | Orchestratori monolitici | `config/engine_factory.py` |
| Stanford | Submodule + worker in core | Solo `integrations/stanford/` importa `reverie/` |
| Persona Stanford | Integrazione più profonda | Adapter slim (Phase 2 futura) |
| PostgreSQL | Parziale | Dual-mode + Alembic |
| Test pytest | ~157 | 85 |
| Harness sim | 1789 righe, 10+ preset | ~260 righe, focus blocking |
| Web UI | Dashboard Smallville | FastAPI + portfolio Astro |
| Benchmark esterni | Concordia, Stanford GA | Auto-parità vs legacy |

---

## Matrice funzionalità

| Feature | Legacy | Nuovo |
|---------|--------|-------|
| Sim tick + proximity | ✅ | ✅ |
| Dialoghi blocking Ollama | ✅ | ✅ |
| Guards meta/italiano/addressee | parziale | ✅ |
| Intent pack + traits/emotions | ✅ | ✅ |
| Memoria per-agente | ✅ | ✅ |
| Reflection + consolidation | ✅ | ✅ |
| Stanford worker + plan | ✅ | ✅ |
| Plan → POI | ✅ | ✅ (reporting fix 2026-07-09) |
| Missioni POI | ✅ | ✅ |
| NEAT + API | ✅ | ✅ |
| NSGS narrative | ✅ | ❌ |
| External shock | ✅ | ❌ |
| Benchmark Concordia | ✅ | ❌ |
| Scenari (nove_soli, shipwreck…) | 31+ | 4 |

---

## Chi vince su cosa

### Nuovo Gen_Agent

- Architettura modulare e boundary rule Stanford
- Parità blocking **dimostrata** (8/8)
- Qualità dialoghi (0 meta, 0 italiano, core 0.898)
- Plan→POI in parità col legacy (24 vs 23 match)
- Riflessioni attive (27/100 tick)
- Postgres + Docker + factory centralizzata
- Manutenibilità (codebase più piccola)

### Gen_Agent legacy

- Harness ricco (NSGS, shock, A/B memoria, NDJSON)
- Plan→POI matching rate alto in preset efficient (1.0)
- ~2× test pytest, più sottosistemi coperti
- Benchmark cross-framework e `gap_analysis.md`
- Web UI completa
- Scenari e documentazione (manuale 15 capitoli)

---

## Gap residui nel fork

1. **Persona Stanford completa** — Phase 2 in `docs/architecture/UPSTREAM_RELATIONSHIP.md`
2. **Velocità blocking** — ~29 s/tick vs ~6 s legacy (dialoghi blocking completi a 3 turni)
3. **Concrete goals usage** — 8 vs 18 legacy (navigazione plan-driven meno frequente)
4. **Harness / telemetria** — no NDJSON full transcript, no ConsenSagent nel report
5. **Scenari** — niente `nove_soli_2187`, shipwreck, debate
6. **NSGS / external shock** — non portati

> Nota: il **Plan→POI matching** (storico punto debole, 3 match) è stato risolto:
> ora 24 match assoluti, in parità col legacy (23), grazie a fallback keyword +
> round-robin e ai nomi dei POI nel prompt.

---

## Come riprodurre

```bash
# 1. Simulazione blocking 100 tick (richiede Ollama, ~45-70 min)
python scripts/run_sim_100_ticks_blocking.py --llm ollama --preset blocking_balanced \
  --report output/sim_blocking_100_v2.json

# 2. Parità qualità (8 soglie)
python scripts/compare_simulations.py --report output/sim_blocking_100_v2.json --skip-legacy

# 3. Confronto quantitativo vs legacy dense_100_efficient
python scripts/compare_simulations.py \
  --report output/sim_blocking_100_v2.json \
  --legacy-report ../Gen_Agent/outputs/test_simulazioni/run_20260611_163750/report_test_100ticks_20260611_164820.json \
  --comparison-out output/comparison_vs_legacy.json
```

---

## Raccomandazione d'uso

| Usa **Nuovo Gen_Agent** se… | Usa **Gen_Agent legacy** se… |
|-----------------------------|------------------------------|
| Sviluppi/deployi in modo modulare | Esplori scenari complessi o ricerca |
| Ti basta `blocking_balanced` + Ollama | Ti serve UI, NSGS, benchmark cross-framework |
| Vuoi Postgres + Docker pulito | Vuoi il manuale completo e 157 test di riferimento |

---

*Aggiornare questo documento dopo ogni run blocking significativa o cambio delle soglie in `compare_simulations.py`.*
