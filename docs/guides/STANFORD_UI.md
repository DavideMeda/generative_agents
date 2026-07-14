# Stanford UI — Integration Guide

The Stanford frontend (`environment/frontend_server`) is a Django 2.2 app that visualizes
simulation state via file polling and can replay recorded runs.

## Integration architecture

```
Modular backend (FastAPI)
  └─ TickRunner
       └─ StanfordExporter   ← writes JSON files to disk
             ↓
environment/frontend_server/storage/{sim_code}/
  movement/{step}.json    ← agent positions per step
  environment/{step}.json ← environment state per step
temp_storage/
  curr_sim_code.json
  curr_step.json

Django frontend_server
  └─ translator/views.py::update_environment()
       └─ reads movement/{step}.json
       └─ responds to the browser
```

The browser polls `/update_environment/` to fetch each step.

## Quick setup (local dev)

**Requirements**
- Python 3.8 recommended for Django 2.2 (3.12+ is incompatible)
- Use a dedicated virtualenv

**Install the Stanford frontend (Django only)**
```bash
cd environment/frontend_server
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # optional
```

**Run services**
```bash
# Terminal A — FastAPI + TickRunner + StanfordExporter
STANFORD_UI_EXPORT=true STANFORD_UI_DIR=environment/frontend_server \
  uvicorn server.main:app --host 0.0.0.0 --port 8000

# Terminal B — Django frontend (port 8001 to avoid conflicts)
cd environment/frontend_server
python manage.py runserver 8001
```
Open http://localhost:8001 to see the Stanford UI.

## Docker Compose profile (recommended)
```bash
# Build images
docker compose -f docker-compose.stanford.yml build

# Run
STANFORD_UI_EXPORT=true STANFORD_UI_DIR=/app/frontend_server \
  docker compose -f docker-compose.stanford.yml up
```
Services:
- `fastapi`: app + TickRunner + StanfordExporter
- `stanford-ui`: Django frontend
Shared volumes mount `environment/frontend_server/storage` and `temp_storage`.

## Key environment variables
- `STANFORD_UI_EXPORT=true` enables file export
- `STANFORD_UI_DIR=...` path to `environment/frontend_server`
- `SIM_CODE=...` folder name under storage/ (default: `gen_agent_run`)

## Troubleshooting
- Missing files in `storage/`: check `STANFORD_UI_EXPORT` and `STANFORD_UI_DIR`.
- Django won’t start: use Python 3.8, recreate venv, run `migrate`.
- No updates in browser: ensure `TickRunner` is calling `StanfordExporter` (check logs).
