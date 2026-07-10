# Stanford UI — Guida di integrazione

Il frontend Stanford (`environment/frontend_server`) è un'applicazione Django 2.2
che visualizza l'esecuzione della simulazione in tempo reale tramite polling
e replay di simulazioni registrate.

---

## Architettura dell'integrazione

```
Backend modulare (FastAPI)
  └─ TickRunner
       └─ StanfordExporter   ← scrive file JSON su disco
             ↓
environment/frontend_server/storage/{sim_code}/
  movement/{step}.json   ← posizioni agenti per step
  environment/{step}.json ← stato ambiente per step
temp_storage/
  curr_sim_code.json
  curr_step.json

Django frontend_server
  └─ translator/views.py::update_environment()
       └─ legge movement/{step}.json
       └─ risponde al browser JavaScript
```

Il browser JavaScript all'interno del frontend Stanford esegue polling su
`/update_environment/` per ricevere aggiornamenti ad ogni step.

---

## Setup rapido (sviluppo locale)

### 1. Requisiti

```bash
# Python 3.8 raccomandato per Django 2.2 (non compatibile con 3.12+)
# Consigliato: ambiente virtuale separato
python -m venv .venv-stanford
```

**Windows:**
```powershell
.venv-stanford\Scripts\activate
pip install -r environment\frontend_server\requirements.txt
```

**Linux/macOS:**
```bash
source .venv-stanford/bin/activate
pip install -r environment/frontend_server/requirements.txt
```

### 2. Configurare variabili d'ambiente backend

Nel file `.env` o come variabili di shell prima di avviare il backend:

```env
# Abilita l'export Stanford (scrive file JSON per il frontend)
STANFORD_UI_EXPORT=true

# Percorso assoluto alla directory environment/frontend_server
STANFORD_UI_DIR=C:/Users/utente/Desktop/Nuovo Gen_Agent/environment/frontend_server

# Codice simulazione (usato per i sottodirectory storage/)
STANFORD_SIM_CODE=gen_agent_run
```

### 3. Avviare il backend

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### 4. Creare le cartelle storage necessarie

```bash
# Windows
New-Item -ItemType Directory -Force "environment\frontend_server\storage\gen_agent_run\personas"
New-Item -ItemType Directory -Force "environment\frontend_server\storage\gen_agent_run\movement"
New-Item -ItemType Directory -Force "environment\frontend_server\storage\gen_agent_run\environment"
New-Item -ItemType Directory -Force "environment\frontend_server\temp_storage"
```

Il `StanfordExporter` le crea automaticamente all'avvio se non esistono.

### 5. Avviare il frontend Stanford

```bash
cd environment\frontend_server
python manage.py migrate
python manage.py runserver 8080
```

### 6. Avviare la simulazione

Tramite REST API del backend:

```bash
curl -X POST http://localhost:8000/api/run/start \
  -H "Content-Type: application/json" \
  -d '{"scenario": "default"}'
```

### 7. Aprire il browser

Navigare su: **http://localhost:8080/simulator_home**

Una volta che il backend ha eseguito almeno un tick e scritto
`temp_storage/curr_step.json`, il frontend mostrerà la simulazione.

---

## Modalità replay

Per visualizzare una simulazione già completata (senza backend attivo):

1. Assicurarsi che i file `storage/{sim_code}/movement/*.json` esistano.
2. Navigare su: `http://localhost:8080/replay/gen_agent_run/0/`
   dove `0` è lo step di partenza.

---

## Docker Compose (profilo Stanford UI)

Un profilo separato è disponibile in `docker-compose.stanford.yml`:

```bash
# Avvia backend + Stanford frontend insieme
docker compose -f docker-compose.base.yml -f docker-compose.stanford.yml up
```

Vedi `docker-compose.stanford.yml` per i dettagli di configurazione.

---

## Note sulla compatibilità

| Componente          | Versione     | Note                                      |
|---------------------|--------------|-------------------------------------------|
| Django              | 2.2          | Vecchio, usa `django.conf.urls.url()` deprecata |
| Python supportato   | 3.8–3.11     | Django 2.2 non supporta Python 3.12+     |
| SQLite              | default      | Nessun DB esterno richiesto per dev       |

Per produzione si consiglia di aggiornare Django a ≥4.x nel fork.

---

## Troubleshooting

**"error_start_backend.html" nel browser:**
Il file `temp_storage/curr_step.json` non esiste ancora.
Avviare il backend e aspettare almeno un tick.

**KeyError nel frontend al passo X:**
Il file `storage/gen_agent_run/movement/{X}.json` manca.
Verificare che `STANFORD_UI_EXPORT=true` sia impostato e che il backend stia girando.

**Import error Django:**
Usare Python ≤ 3.11 nel venv Stanford — Django 2.2 non è compatibile con 3.12+.
