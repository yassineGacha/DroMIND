# DroMIND — Drone Monitoring Intelligence System

DroMIND is a multi-agent AI-powered drone surveillance and monitoring platform. It processes real-time drone video feeds through a LangGraph-orchestrated agent pipeline to perform object detection, terrain/geomorphology analysis, operational safety recommendations, and geofence intrusion detection — all visualized on a real-time military-style HUD dashboard.

---

## Architecture

```
┌──────────────┐    WebSocket     ┌────────────────────────┐    WebSocket    ┌──────────────────┐
│  Mock Drone   │ ──────────────> │   FastAPI Backend       │ ─────────────> │  Next.js Frontend │
│  (Video +     │                 │   (LangGraph Agents)    │                │  (Real-time HUD   │
│   Telemetry)  │ <────────────── │                          │ <───────────── │   Dashboard)      │
└──────────────┘    ACK          └────────────────────────┘                └──────────────────┘
```

### Agent Pipeline (LangGraph Sequential Graph)

```
START → Detection → Geomorphology → Interpretation → Intrusion → END
```

| # | Agent | Model | Description |
|---|-------|-------|-------------|
| 1 | **Detection Agent** | YOLOv8 nano | Runs object detection on each frame. Detects persons, cars, trucks, buses, bicycles, motorcycles, and boats with bounding boxes and confidence scores. Falls back to simulated detections if YOLO is unavailable. |
| 2 | **Geomorphology Agent** | Gemini 1.5 Flash / Ollama llama3.2 | Analyzes terrain, slopes, erosion, water bodies, and landmarks from the video frame + telemetry. Supports multimodal (image+text) when using Gemini. Falls back to coordinate-based terrain simulation. |
| 3 | **Interpretation Agent** | Gemini 1.5 Flash / Ollama llama3.2 | Evaluates operational safety, flight hazards, battery concerns, and landing recommendations. Falls back to rule-based analysis. |
| 4 | **Intrusion Agent** | Rule-based | Checks if detected object centers fall within a predefined geofence ("Restricted Zone Alpha"). Generates severity-rated alerts (high for persons, medium for vehicles). |

VLM calls (Geomorphology + Interpretation) are **throttled to once every 3 seconds** to manage cost and latency. Between calls, cached results are reused.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, LangGraph, LangChain |
| Frontend | Next.js 14, React 18, TypeScript |
| AI Models | YOLOv8 (Ultralytics), Google Gemini 1.5 Flash, Ollama llama3.2 |
| Real-time | WebSockets (bidirectional) |
| Containerization | Docker, Docker Compose |
| LLM Runtime | Ollama (self-hosted) |

---

## Dashboard Features

The frontend is a single-page military/tactical HUD dashboard:

- **Header bar** — System name, server connection status, feed status, perimeter breach indicator
- **Live video viewport** — Base64 frame rendering with SVG overlay: compass HUD, geofence boundary, detection bounding boxes with labels
- **Telemetry panel** — Altitude, ground speed, GPS coordinates, battery (color-coded), heading, signal strength
- **Agent status grid** — All 4 agents with active/alert indicators
- **Geomorphology card** — Terrain analysis text output
- **Operational recommendations** — Safety/flight advice text output
- **LangGraph execution console** — Auto-scrolling terminal-style log viewer with color-coded agent prefixes
- **Alert banner** — Pulsing red bottom banner on geofence breach detection

---

## Docker Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `backend` | Python 3.11-slim | 8000 | FastAPI + LangGraph API server |
| `frontend` | Node 20-slim | 3000 | Next.js dashboard |
| `mock-drone` | (reuses backend image) | — | Simulated drone video streamer |
| `ollama` | ollama/ollama:latest | 11434 | Self-hosted local LLM runtime |
| `ollama-pull-model` | curlimages/curl | — | One-shot init container to pull llama3.2 |

All services are connected via a `dromind-network` bridge network. The `ollama-data` volume persists downloaded models.

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- Node.js 18+ (for local development)
- Google Gemini API Key (optional — system runs on simulated fallback without it)

### Docker Compose (Recommended)

1. Clone the repository:

```bash
git clone https://github.com/yassineGacha/DroMIND.git
cd DroMIND
```

2. (Optional) Create a `.env` file for VLM-powered analysis:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

3. Start all services:

```bash
docker-compose up --build
```

4. Open the dashboard:

```
http://localhost:3000
```

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Mock Drone Simulator

```bash
# Synthetic generated footage (default)
python mock_drone.py

# Using a video file
python mock_drone.py --video path/to/video.mp4

# Using webcam
python mock_drone.py --webcam
```

---

## Project Structure

```
DroMIND/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── agents.py        # 4 AI agent implementations
│   │   │   ├── graph.py         # LangGraph sequential workflow
│   │   │   └── state.py         # Shared AgentState TypedDict
│   │   └── main.py              # FastAPI app (REST + WebSocket)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── yolov8n.pt               # YOLOv8 nano model weights
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Dashboard UI (single-page)
│   │   ├── layout.tsx           # Root layout with Google Fonts
│   │   └── globals.css          # Military HUD theme
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml           # 5-service orchestration
├── mock_drone.py                # Drone video stream simulator
├── drone.mp4                    # Sample drone footage
└── README.md
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/analyze` | Manual single-frame analysis |
| `WS` | `/api/ws?client_type=drone` | Drone video + telemetry ingestion |
| `WS` | `/api/ws?client_type=browser` | Real-time intelligence broadcast |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | No | — | Google Gemini API key for VLM-powered terrain analysis. Without it, the system uses simulated fallback analysis. |
| `OLLAMA_BASE_URL` | No | `http://ollama:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama3.2` | Ollama model name for local LLM inference |

---

## License

MIT
