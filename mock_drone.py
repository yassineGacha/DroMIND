import asyncio
import base64
import cv2
import json
import numpy as np
import time
import argparse
import sys
import math

try:
    import websockets
except ImportError:
    print("Error: 'websockets' library is required to run the mock drone.")
    print("Please install it using: pip install websockets")
    sys.exit(1)

# Helper to encode OpenCV image to base64 string
def encode_frame_to_base64(frame):
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{jpg_as_text}"

# Class to generate synthetic drone footage frames
class DroneVideoSimulator:
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.frame_count = 0
        
    def generate_frame(self, t):
        # 1. Base terrain canvas (light green pasture)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (34, 139, 34)  # Forest green in BGR
        
        # 2. Draw a river cutting diagonally (Geomorphology landscape feature)
        # We make the river bend over time using a sine wave
        river_pts = []
        for y in range(0, self.height, 10):
            x = int(100 + 40 * math.sin(y * 0.01 + t * 0.5) + y * 0.4)
            river_pts.append((x, y))
            
        # Draw river path
        for i in range(len(river_pts) - 1):
            cv2.line(frame, river_pts[i], river_pts[i+1], (238, 104, 0), 22) # Royal Blue BGR
            cv2.line(frame, river_pts[i], river_pts[i+1], (250, 180, 50), 12) # Bright Blue BGR
            
        # 3. Draw a highway (gray road) crossing horizontally
        cv2.rectangle(frame, (0, 180), (self.width, 240), (120, 120, 120), -1)
        cv2.line(frame, (0, 210), (self.width, 210), (255, 255, 255), 2) # Center line
        
        # 4. Draw a "Restricted Zone Alpha" geofence visualization (yellow/red transparent hash)
        # Coordinates match backend: X (250, 500), Y (100, 400)
        overlay = frame.copy()
        cv2.rectangle(overlay, (250, 100), (500, 400), (0, 0, 255), -1) # Red overlay
        # Blend overlay (semi-transparent restricted area)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
        cv2.rectangle(frame, (250, 100), (500, 400), (0, 165, 255), 1) # Orange border
        
        # 5. Draw a moving car (traveling on the highway)
        # Position oscillates horizontally
        car_x = int(150 + 50 * math.sin(t * 0.2))
        car_y = int(200 + 20 * math.cos(t * 0.2))
        
        # Car body (Red)
        cv2.rectangle(frame, (car_x, car_y), (car_x + 110, car_y + 40), (0, 0, 220), -1)
        # Car windows (Cyan)
        cv2.rectangle(frame, (car_x + 70, car_y + 5), (car_x + 100, car_y + 35), (200, 200, 0), -1)
        # Car wheels
        cv2.circle(frame, (car_x + 20, car_y + 40), 10, (20, 20, 20), -1)
        cv2.circle(frame, (car_x + 90, car_y + 40), 10, (20, 20, 20), -1)
        
        # 6. Draw a moving person (walking around)
        # Position moves in a circle near the restricted geofence edge
        person_x = int(300 + 40 * math.cos(t * 0.5))
        person_y = int(250 + 40 * math.sin(t * 0.5))
        
        # Pedestrian shape (stick figure)
        # Head
        cv2.circle(frame, (person_x + 20, person_y + 20), 8, (0, 255, 255), -1) # Yellow head
        # Body
        cv2.line(frame, (person_x + 20, person_y + 28), (person_x + 20, person_y + 60), (0, 255, 255), 3)
        # Arms
        cv2.line(frame, (person_x + 5, person_y + 40), (person_x + 35, person_y + 40), (0, 255, 255), 2)
        # Legs
        cv2.line(frame, (person_x + 20, person_y + 60), (person_x + 10, person_y + 85), (0, 255, 255), 2)
        cv2.line(frame, (person_x + 20, person_y + 60), (person_x + 30, person_y + 85), (0, 255, 255), 2)
        
        # 7. Compass & Pitch Ladder HUD display directly on raw footage (military/drone style)
        cv2.putText(frame, "ALT: " + f"{15.0 + 3.0 * math.sin(t * 0.1):.1f}m", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, "CAM LIVE [REC]", (self.width - 160, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Telemetry info
        cv2.putText(frame, "LAT: 37.77490", (20, self.height - 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, "LON:-122.41940", (20, self.height - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        self.frame_count += 1
        return frame

# Main async function to stream video to FastAPI websocket
async def stream_drone_feed(args):
    uri = f"ws://{args.host}:{args.port}/api/ws?client_type=drone"
    print(f"Connecting mock drone camera to: {uri} ...")
    
    # Initialize generator
    simulator = DroneVideoSimulator()
    
    # Setup video capture if requested
    cap = None
    if args.video:
        import os
        if not os.path.exists(args.video):
            print(f"Error: Video file '{args.video}' not found.")
            print("Please provide a valid video file path using --video argument.")
            print("Example: python mock_drone.py --video path/to/your/video.mp4")
            print("Or use --webcam for live camera feed.")
            sys.exit(1)
        print(f"Opening video file source: {args.video}")
        cap = cv2.VideoCapture(args.video)
    elif args.webcam:
        print("Opening webcam device index 0...")
        cap = cv2.VideoCapture(0)
        
    start_time = time.time()
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Drone WebSocket connected successfully! Commencing stream...")
                
                # Stream Loop
                while True:
                    t = time.time() - start_time
                    
                    # 1. Grab image frame
                    if cap is not None and cap.isOpened():
                        ret, frame = cap.read()
                        if not ret:
                            # Loop video
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, frame = cap.read()
                            if not ret:
                                print("Error reading video frame. Falling back to simulator.")
                                cap.release()
                                cap = None
                                continue
                        # Resize for streaming speed consistency
                        frame = cv2.resize(frame, (640, 480))
                    else:
                        frame = simulator.generate_frame(t)
                    
                    # 2. Generate simulated telemetry
                    altitude = 12.5 + 2.5 * math.sin(t * 0.08)
                    speed = 4.8 + 1.2 * math.cos(t * 0.15)
                    heading = (120.0 + t * 2) % 360
                    battery = max(15, int(98 - t * 0.15))
                    signal = int(92 + 5 * math.sin(t * 0.3))
                    
                    # Base GPS coordinates + minor offset drift
                    lat = 37.7749 + 0.0001 * math.sin(t * 0.02)
                    lng = -122.4194 + 0.0001 * math.cos(t * 0.02)
                    
                    telemetry_payload = {
                        "altitude": round(altitude, 2),
                        "speed": round(speed, 2),
                        "heading": round(heading, 1),
                        "latitude": lat,
                        "longitude": lng,
                        "battery": battery,
                        "signal": signal
                    }
                    
                    # 3. Base64 encode the frame
                    image_b64 = encode_frame_to_base64(frame)
                    
                    # 4. Compile message
                    message = {
                        "image": image_b64,
                        "telemetry": telemetry_payload
                    }
                    
                    # Send payload
                    await websocket.send(json.dumps(message))
                    
                    # Wait for backend acknowledgment response
                    response_raw = await websocket.recv()
                    response = json.loads(response_raw)
                    
                    # Print brief status console feedback
                    print(f"\rStream Sent: Alt={altitude:.1f}m, Batt={battery}%, Speed={speed:.1f}m/s | Backend status: {response.get('status')}", end="", flush=True)
                    
                    # Throttle rate to control framerate (~10 FPS is good for local developer demo)
                    await asyncio.sleep(0.1)
                    
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            print(f"\nConnection failed ({e}). Retrying in 3 seconds...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"\nUnexpected streaming error: {e}")
            await asyncio.sleep(3)
            
    if cap is not None:
        cap.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DroMIND Mock Drone Video & Telemetry Streamer Client.")
    parser.add_argument("--host", default="localhost", help="FastAPI backend host name or IP address.")
    parser.add_argument("--port", default="8000", help="FastAPI backend WebSocket port.")
    parser.add_argument("--video", default="drone.mp4", help="Path to local mp4 video file source to stream.")
    parser.add_argument("--webcam", action="store_true", help="Use local connected webcam device instead of generator.")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(stream_drone_feed(args))
    except KeyboardInterrupt:
        print("\nDrone stream terminated by operator control.")
