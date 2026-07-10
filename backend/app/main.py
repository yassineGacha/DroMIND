import time
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agents.graph import dro_mind_graph
from app.agents.state import AgentState

app = FastAPI(
    title="DroMIND AI Backend",
    description="FastAPI Backend for DroMIND drone video streaming and multi-agent AI orchestration.",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for the latest processed state
latest_drone_state: Dict[str, Any] = {
    "frame_b64": "",
    "telemetry": {
        "altitude": 0.0,
        "speed": 0.0,
        "heading": 0.0,
        "latitude": 37.7749,
        "longitude": -122.4194,
        "battery": 100,
        "signal": 100
    },
    "detections": [],
    "geomorphology": "Awaiting drone feed connection...",
    "operational_interpretation": "System standing by.",
    "intrusion_alerts": [],
    "agent_logs": []
}

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_browsers: List[WebSocket] = []

    async def connect_browser(self, websocket: WebSocket):
        await websocket.accept()
        self.active_browsers.append(websocket)
        print(f"Browser connected. Total browsers: {len(self.active_browsers)}")

    def disconnect_browser(self, websocket: WebSocket):
        if websocket in self.active_browsers:
            self.active_browsers.remove(websocket)
            print(f"Browser disconnected. Total browsers: {len(self.active_browsers)}")

    async def broadcast_to_browsers(self, data: dict):
        for connection in self.active_browsers:
            try:
                # We send the processed data including frame and agent outputs
                await connection.send_json(data)
            except Exception as e:
                # Connection might have closed unexpectedly
                pass

manager = ConnectionManager()

# Global state to track throttling of VLM calls to save cost/latency
last_vlm_run_time = 0.0
cached_geomorphology = "Slightly rolling terrain, clay-loam topsoil with light grassy vegetation cover."
cached_operational = "Visual flight conditions nominal. Ground landing suitability: High."

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "yolo": "loaded"
        }
    }

class FrameAnalysisRequest(BaseModel):
    frame_b64: str
    telemetry: Dict[str, Any]

@app.post("/api/analyze")
async def analyze_frame(payload: FrameAnalysisRequest):
    """
    REST endpoint to analyze a single frame manually.
    """
    initial_state: AgentState = {
        "frame_b64": payload.frame_b64,
        "telemetry": payload.telemetry,
        "detections": [],
        "geomorphology": "",
        "operational_interpretation": "",
        "intrusion_alerts": [],
        "agent_logs": [{"agent": "System", "message": "Manual REST trigger received."}]
    }
    
    try:
        final_state = dro_mind_graph.invoke(initial_state)
        # Clean up b64 for display in JSON response if needed, or return full state
        return final_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, client_type: str = "browser"):
    """
    Combined WebSocket endpoint.
    - If client_type is 'browser': the browser connects to receive real-time drone data feeds.
    - If client_type is 'drone': the mock drone streams frame data and telemetry.
    """
    global last_vlm_run_time, cached_geomorphology, cached_operational, latest_drone_state
    
    if client_type == "browser":
        await manager.connect_browser(websocket)
        try:
            # Send initial state so browser isn't blank
            await websocket.send_json(latest_drone_state)
            while True:
                # Keep connection alive
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect_browser(websocket)
            
    elif client_type == "drone":
        await websocket.accept()
        print("Drone camera feed connected via WebSockets.")
        try:
            while True:
                data = await websocket.receive_json()
                
                frame_b64 = data.get("image", "")
                telemetry = data.get("telemetry", {})
                
                # Check throttle rate for VLM calls (Gemini).
                # Only execute full Gemini agent pipeline once every 3.0 seconds to keep streams smooth.
                current_time = time.time()
                run_vlm = False
                if current_time - last_vlm_run_time > 3.0:
                    run_vlm = True
                    
                # Formulate graph state
                initial_state: AgentState = {
                    "frame_b64": frame_b64,
                    "telemetry": telemetry,
                    "detections": [],
                    "geomorphology": cached_geomorphology if not run_vlm else "",
                    "operational_interpretation": cached_operational if not run_vlm else "",
                    "intrusion_alerts": [],
                    "agent_logs": [{"agent": "Orchestrator", "message": f"Frame received. VLM execution: {run_vlm}"}]
                }
                
                # Execute LangGraph Multi-Agent pipeline
                try:
                    # In real-world, we run this in a background thread or async executor if blocked, 
                    # but since it's very fast, we run it directly.
                    final_state = dro_mind_graph.invoke(initial_state)
                    
                    # Update cache if VLM was executed
                    if run_vlm:
                        last_vlm_run_time = current_time
                        cached_geomorphology = final_state.get("geomorphology", cached_geomorphology)
                        cached_operational = final_state.get("operational_interpretation", cached_operational)
                    else:
                        # Ensure we populate the state with cached analysis if not run
                        final_state["geomorphology"] = cached_geomorphology
                        final_state["operational_interpretation"] = cached_operational
                        
                    # Save globally
                    latest_drone_state = {
                        "frame_b64": frame_b64,
                        "telemetry": telemetry,
                        "detections": final_state.get("detections", []),
                        "geomorphology": final_state.get("geomorphology", ""),
                        "operational_interpretation": final_state.get("operational_interpretation", ""),
                        "intrusion_alerts": final_state.get("intrusion_alerts", []),
                        "agent_logs": final_state.get("agent_logs", [])
                    }
                    
                    # Broadcast processed frames and intelligence payload to Next.js browsers
                    await manager.broadcast_to_browsers(latest_drone_state)
                    
                    # Respond back to the drone to acknowledge frame
                    await websocket.send_json({"status": "processed"})
                    
                except Exception as e:
                    print(f"Error running multi-agent graph: {e}")
                    await websocket.send_json({"status": "error", "message": str(e)})
                    
        except WebSocketDisconnect:
            print("Drone camera feed disconnected.")
        except Exception as e:
            print(f"Drone WebSocket error: {e}")
            
    else:
        # Invalid client type
        await websocket.accept()
        await websocket.send_json({"error": "Invalid client_type. Must be 'browser' or 'drone'"})
        await websocket.close()
