# DroMIND - Drone Monitoring Intelligence System

DroMIND is a multi-agent AI-powered drone surveillance and monitoring system. It processes real-time drone video feeds, performs object detection, terrain analysis, operational recommendations, and geofence intrusion detection using a LangGraph orchestrated agent pipeline.

## Architecture

```
┌─────────────┐     WebSocket      ┌──────────────────────┐     WebSocket     ┌─────────────────┐
│  Mock Drone  │ ─────────────────> │   FastAPI Backend     │ ────────────────> │  Next.js Frontend│
│  (Video +    │                    │   (LangGraph Agents)  │                    │  (Real-time      │
│   Telemetry) │ <───────────────── │                        │ <──────────────── │   Dashboard)     │
└─────────────┘     ACK            └──────────────────────┘                    └─────────────────┘
```

### Agent Pipeline (LangGraph)

1. **Detection Agent** - YOLOv8 object detection (person, car, truck, etc.)
2. **Geomorphology Agent** - Terrain and landscape analysis via Gemini VLM
3. **Interpretation Agent** - Operational safety and flight recommendations
4. **Intrusion Agent** - Geofence boundary breach detection

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI, LangGraph, LangChain |
| Frontend | Next.js 14, React, TypeScript |
| AI Models | YOLOv8, Google Gemini 1.5 Flash |
| Real-time | WebSockets |
| Containerization | Docker, Docker Compose |

## Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- Node.js 18+ (for local development)
- Google Gemini API Key (optional, for VLM-powered analysis)

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:

```bash
git clone <your-repo-url>
cd DROMIND
```

2. Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

3. Start all services:

```bash
docker-compose up --build
```

4. Open the dashboard in your browser:

```
http://localhost:3000
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js dashboard |
| Backend | 8000 | FastAPI + LangGraph API |
| Mock Drone | - | Video stream simulator |

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
# Using synthetic generated footage
python mock_drone.py

# Using a video file
python mock_drone.py --video path/to/video.mp4

# Using webcam
python mock_drone.py --webcam
```

## Project Structure

```
DROMIND/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── agents.py       # Agent implementations
│   │   │   ├── graph.py        # LangGraph workflow
│   │   │   └── state.py        # Shared state definitions
│   │   └── main.py             # FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   └── yolov8n.pt              # YOLOv8 nano model weights
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Dashboard UI
│   │   ├── layout.tsx          # App layout
│   │   └── globals.css         # Global styles
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
├── mock_drone.py               # Mock drone video streamer
├── drone.mp4                   # Sample drone footage
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | No | Google Gemini API key for VLM analysis. Without it, the system uses simulated fallback analysis. |

## License

MIT
