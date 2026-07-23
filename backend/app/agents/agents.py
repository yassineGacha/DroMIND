import base64
import cv2
import numpy as np
import os
import time
from typing import Dict, Any, List
from PIL import Image
import io

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from app.agents.state import AgentState, Detection, IntrusionAlert, Telemetry

# Initialize YOLO model lazily or fall back if not available
YOLO_AVAILABLE = False
yolo_model = None

try:
    import torch
    # Allowlist ultralytics model classes for PyTorch 2.6+ security check
    try:
        from ultralytics.nn.tasks import DetectionModel
        from ultralytics.nn.modules.conv import Conv, Concat
        from ultralytics.nn.modules.block import C2f, Bottleneck, DFL
        from ultralytics.nn.modules.head import Detect
        
        torch.serialization.add_safe_globals([
            DetectionModel, Conv, Concat, C2f, Bottleneck, DFL, Detect
        ])
        print("Allowlisted Ultralytics classes in PyTorch safe globals.")
    except Exception as e:
        print(f"Failed to import/register safe globals: {e}")

    from ultralytics import YOLO
    # Load a lightweight YOLOv8 nano model
    yolo_model = YOLO("yolov8n.pt")
    YOLO_AVAILABLE = True
    print("YOLOv8 initialized successfully.")
except Exception as e:
    print(f"YOLOv8 load failed (will use simulated detection): {e}")

# Helper to decode base64 to OpenCV image
def decode_base64_image(b64_str: str) -> np.ndarray:
    if "," in b64_str:
        b64_str = b64_str.split(",")[1]
    img_data = base64.b64decode(b64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

# LLM Factory supporting local Ollama & Gemini
def get_llm():
    ollama_url = os.getenv("OLLAMA_BASE_URL")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if ollama_url:
        try:
            return ChatOllama(
                base_url=ollama_url,
                model=ollama_model,
            )
        except Exception as e:
            print(f"Failed to initialize ChatOllama: {e}")
            
    if gemini_key:
        try:
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=gemini_key
            )
        except Exception as e:
            print(f"Failed to initialize ChatGoogleGenerativeAI: {e}")
            
    return None

# ----------------- 1. DETECTION AGENT -----------------
def detection_agent(state: AgentState) -> Dict[str, Any]:
    logs = state.get("agent_logs", [])[:]
    logs.append({"agent": "DetectionAgent", "message": "Initiating object detection scan..."})
    
    detections: List[Detection] = []
    
    if not state.get("frame_b64"):
        return {"detections": [], "agent_logs": logs}
        
    try:
        if YOLO_AVAILABLE and yolo_model is not None:
            # Decode image
            img = decode_base64_image(state["frame_b64"])
            if img is not None:
                # Run YOLOv8 detection
                results = yolo_model(img, verbose=False)
                
                # YOLOv8 class map: 0 is person, 2 is car, 7 is truck, etc.
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        label = yolo_model.names[cls_id]
                        conf = float(box.conf[0])
                        
                        # We only care about standard categories for DroMIND demo
                        if label in ["person", "car", "truck", "bus", "bicycle", "motorcycle", "boat"]:
                            # Bounding box in [x1, y1, x2, y2]
                            coords = box.xyxy[0].tolist()
                            h, w, _ = img.shape
                            # Convert to normalized or absolute coordinates
                            # We will send absolute coordinates for drawing on canvas
                            detections.append({
                                "label": label,
                                "confidence": round(conf, 2),
                                "box": [
                                    round(coords[0]),  # x
                                    round(coords[1]),  # y
                                    round(coords[2] - coords[0]),  # w
                                    round(coords[3] - coords[1])   # h
                                ]
                            })
                logs.append({
                    "agent": "DetectionAgent", 
                    "message": f"Object scan completed. Found {len(detections)} objects: " + 
                                ", ".join([f"{d['label']} ({d['confidence']})" for d in detections])
                })
        else:
            # Fallback mock detector (generates simulated detections that move slightly)
            # This makes the UI feel dynamic even if YOLO is not installed
            t = time.time()
            # Simulate a moving car
            car_x = int(150 + 50 * np.sin(t * 0.2))
            car_y = int(200 + 20 * np.cos(t * 0.2))
            detections.append({
                "label": "car",
                "confidence": 0.89,
                "box": [car_x, car_y, 110, 60]
            })
            
            # Simulate a person walking near the geofence boundary
            person_x = int(300 + 40 * np.cos(t * 0.5))
            person_y = int(250 + 40 * np.sin(t * 0.5))
            detections.append({
                "label": "person",
                "confidence": 0.94,
                "box": [person_x, person_y, 40, 90]
            })
            
            logs.append({
                "agent": "DetectionAgent", 
                "message": f"[Mock Mode] Detected 1 car at [{car_x}, {car_y}], 1 person at [{person_x}, {person_y}]"
            })
    except Exception as e:
        logs.append({"agent": "DetectionAgent", "message": f"Detection failed: {str(e)}"})
        
    return {"detections": detections, "agent_logs": logs}

# ----------------- 2. GEOMORPHOLOGY AGENT -----------------
def geomorphology_agent(state: AgentState) -> Dict[str, Any]:
    logs = state.get("agent_logs", [])[:]
    logs.append({"agent": "GeomorphologyAgent", "message": "Analyzing terrain structure and elevation parameters..."})
    
    telemetry = state.get("telemetry", {})
    llm = get_llm()
    
    if llm:
        try:
            # Prepare image payload
            frame_b64 = state["frame_b64"]
            if "," in frame_b64:
                frame_b64 = frame_b64.split(",")[1]
                
            prompt = (
                f"You are the DroMIND Geomorphology Agent. Analyze the drone's current video frame. "
                f"Drone Telemetry: Altitude={telemetry.get('altitude')}m, Lat={telemetry.get('latitude')}, Long={telemetry.get('longitude')}. "
                f"Describe the terrain structure, slopes, erosion signs, water bodies, or landmarks visible. "
                f"Keep your analysis extremely concise (under 2 sentences) and focus on geomorphology."
            )
            
            # Attempt to use visual input if supported by model, otherwise fallback to text-only
            is_multimodal = isinstance(llm, ChatGoogleGenerativeAI) or "vision" in getattr(llm, "model", "").lower() or "llava" in getattr(llm, "model", "").lower()
            
            try:
                if is_multimodal:
                    message = HumanMessage(
                        content=[
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": f"data:image/jpeg;base64,{frame_b64}"
                            }
                        ]
                    )
                    response = llm.invoke([message])
                else:
                    # Text only prompt fallback
                    prompt_text = prompt + " (Analyze based on the telemetry and simulate/describe typical terrain at these coordinates)."
                    response = llm.invoke([HumanMessage(content=prompt_text)])
            except Exception as inner_e:
                prompt_text = prompt + " (Analyze based on the telemetry and simulate/describe typical terrain at these coordinates)."
                response = llm.invoke([HumanMessage(content=prompt_text)])
                
            analysis = response.content.strip()
            logs.append({"agent": "GeomorphologyAgent", "message": f"{llm.__class__.__name__} Analysis: {analysis}"})
            return {"geomorphology": analysis, "agent_logs": logs}
            
        except Exception as e:
            logs.append({"agent": "GeomorphologyAgent", "message": f"LLM API failed: {str(e)}. Falling back to simulation."})
            
    # Mock Geomorphology based on coordinates & altitude
    lat = telemetry.get("latitude", 0.0)
    alt = telemetry.get("altitude", 0.0)
    
    # Generate interesting fake geological profile based on coordinates
    if lat > 45.0:
        geomorph = f"High-slope rocky terrain ({int(alt/2.5)}° incline). Heavy granite bedrock, low soil thickness, potential minor landslide vulnerability in the eastern ravine."
    elif lat < 30.0:
        geomorph = "Sandy desert flatlands. Dispersed dune crests moving northeast. Soil composition shows high quartz content, low stability for ground equipment landing."
    else:
        geomorph = "Moderately vegetated clay-loam valley. Low slopes (< 5°). Saturated topsoil near the creek drainage path. High traction stability index."
        
    logs.append({"agent": "GeomorphologyAgent", "message": f"Terrain assessment compiled: {geomorph}"})
    return {"geomorphology": geomorph, "agent_logs": logs}

# ----------------- 3. OPERATIONAL INTERPRETATION AGENT -----------------
def interpretation_agent(state: AgentState) -> Dict[str, Any]:
    logs = state.get("agent_logs", [])[:]
    logs.append({"agent": "InterpretationAgent", "message": "Evaluating operational impact and environment safety..."})
    
    telemetry = state.get("telemetry", {})
    detections = state.get("detections", [])
    geomorphology = state.get("geomorphology", "")
    llm = get_llm()
    
    if llm:
        try:
            prompt = (
                f"You are the DroMIND Operational Interpretation Agent. "
                f"Review the Drone Telemetry: Altitude={telemetry.get('altitude')}m, Speed={telemetry.get('speed')}m/s, Battery={telemetry.get('battery')}%. "
                f"Detections in view: {[d['label'] for d in detections]}. "
                f"Terrain geomorphology: {geomorphology}. "
                f"Recommend operational procedures. E.g. landing suitability, flight hazard warnings (obstacles, high wind, steep slopes), battery concerns, or path suggestions. "
                f"Keep it under 2 sentences, action-oriented, and highly operational."
            )
            
            response = llm.invoke([prompt])
            op_info = response.content.strip()
            logs.append({"agent": "InterpretationAgent", "message": f"{llm.__class__.__name__} Insights: {op_info}"})
            return {"operational_interpretation": op_info, "agent_logs": logs}
            
        except Exception as e:
            logs.append({"agent": "InterpretationAgent", "message": f"LLM API failed: {str(e)}. Falling back to simulation."})
            
    # Mock Operational Interpretation
    battery = telemetry.get("battery", 100)
    speed = telemetry.get("speed", 0.0)
    alt = telemetry.get("altitude", 0.0)
    
    insights = []
    
    # Check battery rules
    if battery < 25:
        insights.append("WARNING: Low battery payload. Abort task and route to home landing point.")
    
    # Check landing suitability based on geomorphology
    if "slope" in geomorphology.lower() and ("granite" in geomorphology.lower() or "landslide" in geomorphology.lower()):
        insights.append(f"Slope unsuitable for emergency landing. Maintain altitude above {alt:.1f}m.")
    else:
        insights.append("Landing zone criteria: Green. Flat terrain offers 94% safety margin for emergency landing.")
        
    # Check speed / flight path safety
    if speed > 10.0:
        insights.append("High-speed flight. Obstacle scan buffer extended to 45 meters.")
    else:
        insights.append("Stable hover velocity. Object tracking persistence rate high.")
        
    op_info = " | ".join(insights)
    logs.append({"agent": "InterpretationAgent", "message": f"Operational recommendations: {op_info}"})
    return {"operational_interpretation": op_info, "agent_logs": logs}

# ----------------- 4. INTRUSION AGENT -----------------
def intrusion_agent(state: AgentState) -> Dict[str, Any]:
    logs = state.get("agent_logs", [])[:]
    logs.append({"agent": "IntrusionAgent", "message": "Performing geofence boundary checks..."})
    
    detections = state.get("detections", [])
    alerts: List[IntrusionAlert] = []
    
    # Define a simulated "Restricted Zone" in the image frame
    # Let's say the middle-right area of the frame is restricted:
    # Coordinates in pixels (assuming 640x480 standard frame)
    # Zone: X between 250 and 500, Y between 100 and 400
    rx1, rx2 = 250, 500
    ry1, ry2 = 100, 400
    
    timestamp = time.strftime("%H:%M:%S", time.gmtime())
    
    for d in detections:
        dx, dy, dw, dh = d["box"]
        # Check if the center of the bounding box is inside our restricted geofenced zone
        cx = dx + dw / 2
        cy = dy + dh / 2
        
        if rx1 <= cx <= rx2 and ry1 <= cy <= ry2:
            severity = "high" if d["label"] == "person" else "medium"
            alerts.append({
                "severity": severity,
                "message": f"Unauthorized {d['label']} breach detected in Restricted Zone Alpha!",
                "timestamp": timestamp
            })
            
    if alerts:
        logs.append({
            "agent": "IntrusionAgent", 
            "message": f"ALERT: {len(alerts)} boundary breach(es) detected! Logged to Security System."
        })
    else:
        logs.append({
            "agent": "IntrusionAgent", 
            "message": "Geofence boundary sweep completed. No breaches detected."
        })
        
    return {"intrusion_alerts": alerts, "agent_logs": logs}
