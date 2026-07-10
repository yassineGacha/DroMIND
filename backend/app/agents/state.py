from typing import TypedDict, List, Dict, Any, Optional

class Telemetry(TypedDict):
    altitude: float      # in meters
    speed: float         # in m/s
    heading: float       # in degrees (0-360)
    latitude: float
    longitude: float
    battery: int         # percentage (0-100)
    signal: int          # percentage (0-100)

class Detection(TypedDict):
    label: str
    confidence: float
    box: List[float]     # [x, y, width, height] normalized or relative coordinates

class IntrusionAlert(TypedDict):
    severity: str        # "low", "medium", "high"
    message: str
    timestamp: str

class AgentState(TypedDict):
    # Inputs
    frame_b64: str                  # Base64 encoded JPEG image
    telemetry: Telemetry
    
    # Outputs from agents
    detections: List[Detection]
    geomorphology: str
    operational_interpretation: str
    intrusion_alerts: List[IntrusionAlert]
    
    # Internal orchestration logs
    agent_logs: List[Dict[str, str]]  # list of {"agent": str, "message": str}
