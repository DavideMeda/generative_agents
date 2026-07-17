# Capture the demo GIF

The landing page and README expect a short loop at:

- `docs/assets/demo.gif` (repo / README)
- `site/public/demo.gif` (Astro site — copy the same file)

## Steps (Windows)

1. Open a terminal in the project root and start the dashboard:

```bash
pip install -e ".[dev]"
set LLM_PROVIDER=mock
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

2. Open `http://127.0.0.1:8000` in the browser.

3. Start a short simulation from the UI (or run a 20-tick mock in another terminal):

```bash
python scripts/run_sim_100_ticks_blocking.py --llm mock --ticks 20 --preset fast
```

4. Record the browser window with [ScreenToGif](https://www.screentogif.com/) (free):
   - 5–10 seconds of agents moving / interactions
   - Export as GIF, aim for **under 5 MB**
   - Resolution ~1280×720 is enough

5. Save as `docs/assets/demo.gif`, then copy:

```bash
copy docs\assets\demo.gif site\public\demo.gif
```

6. Commit both files and push. The site build will pick up `site/public/demo.gif`.

## Optional: Ollama instead of mock

Use a real model for a richer-looking clip (slower):

```bash
ollama pull llama3.2:3b
set LLM_PROVIDER=ollama
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Until the GIF exists, the website shows a terminal-style placeholder automatically.
