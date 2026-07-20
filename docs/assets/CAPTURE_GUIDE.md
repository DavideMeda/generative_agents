# Visual Assets Capture Guide

This guide shows how to create screenshots and video demos for the project.

## 1. Screenshot: Web UI Dashboard

**Purpose:** Show the live simulation dashboard for README and site homepage.

**Steps:**
1. Start the server:
   ```bash
   docker compose up
   ```
2. Open `http://localhost:8000` in a browser
3. Start a simulation (click "Start" or use the API)
4. Wait for agents to appear and interact
5. Take a screenshot showing:
   - Agent positions on the map
   - Real-time stats (tick count, interactions, dialogues)
   - Memory/dialogue panel (if visible)

**Recommended tools:**
- **macOS:** `Cmd+Shift+4` (native)
- **Windows:** `Win+Shift+S` (Snipping Tool)
- **Linux:** `gnome-screenshot` or Flameshot

**Dimensions:** 1920×1080 or 2560×1440 (16:9 aspect ratio)

**Save as:**
- `site/public/dashboard-screenshot.png` (for website)
- `docs/assets/dashboard-screenshot.png` (for README)

---

## 2. Video Demo (30-60 seconds)

**Purpose:** Show simulation in action for README, site hero, and social media.

**Content:**
1. Show terminal: `python examples/ollama_simple.py`
2. Watch simulation output (ticks, interactions, dialogues)
3. Switch to browser: live dashboard with agents moving
4. Highlight a dialogue happening in real time
5. Show final stats

**Recommended tools:**
- **macOS:** QuickTime Player (File → New Screen Recording)
- **Windows:** OBS Studio (free, open-source)
- **Linux:** SimpleScreenRecorder or OBS Studio

**Export settings:**
- Format: MP4 (H.264)
- Resolution: 1920×1080
- Framerate: 30 fps
- Bitrate: 5-8 Mbps

**Convert to GIF (optional, for README):**
```bash
# Using ffmpeg (install: brew install ffmpeg / apt install ffmpeg)
ffmpeg -i demo.mp4 -vf "fps=15,scale=1280:-1:flags=lanczos" -c:v gif demo.gif

# Or use online converter: https://ezgif.com/video-to-gif
```

**Save as:**
- `site/public/demo.mp4` (for website)
- `docs/assets/demo.gif` (for README, max 10 MB)

---

## 3. Open Graph Image (Social Media Preview)

**Purpose:** When the site is shared on Twitter/LinkedIn/Facebook, this image appears.

**Content:**
- Project name: "New Gen Agent"
- Tagline: "Cognitive Generative Agents"
- Visual: terminal output or dashboard screenshot with dark overlay
- Dimensions: **1200×630 px** (Open Graph standard)

**Tools:**
- Figma (free): https://figma.com
- Canva (free): https://canva.com
- Photopea (free, browser): https://photopea.com

**Template suggestion:**
- Background: Dark gradient (#0a0a0a → #0d0d0d)
- Title: "New Gen Agent" (Syne Bold, 72pt, white)
- Subtitle: "Cognitive Generative Agents" (IBM Plex Mono, 24pt, #00d9ff)
- Footer: "github.com/DavideMeda/new-gen-agent" (12pt, #666)

**Save as:**
- `site/public/og-image.png` (1200×630 px)

---

## 4. Favicon

Already present at `site/public/favicon.svg`. If you want to update:

**Steps:**
1. Design a simple icon (16×16 / 32×32 / 64×64)
2. Export as SVG (vector, scales to any size)
3. Replace `site/public/favicon.svg`

---

## Notes

- **Timing:** Capture assets after ensuring the simulation runs smoothly (no errors, natural interactions)
- **Lighting:** Use dark theme for all captures (matches site aesthetic)
- **Privacy:** Don't include API keys or sensitive data in screenshots
- **Compression:** Use TinyPNG (https://tinypng.com) to reduce PNG file sizes
