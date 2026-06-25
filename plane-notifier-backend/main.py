import time
import threading
import json
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_db_connection, get_settings

app = FastAPI(title="Plane Overhead Notifier API")

# Allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Handle stale connections cleanly
                pass

manager = ConnectionManager()

# --- Shared Threading State ---
# Safe container for passing data between background thread and web layer
live_system_state = {
    "current_planes": [],
    "session_count": 0,
    "last_poll_time": 0
}

# --- Core Polling & Logic Thread ---
def background_polling_worker():
    """
    Runs continuously in its own thread. Inherits your existing Step 1-10 polling 
    logic without blocking web requests or API calls.
    """
    print("🚀 Background worker thread tracking aircraft started.")
    
    # Configuration matches your established home base
    HOME_LAT = 25.336472
    HOME_LON = 55.392139
    
    while True:
        try:
            current_settings = get_settings()
            radius = float(current_settings.get("alert_radius", 3.0))
            
            # 1. Poll live data endpoint
            url = f"https://api.airplanes.live/v2/point/{HOME_LAT}/{HOME_LON}/{radius}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                aircraft_list = data.get("ac", [])
                
                # Update our in-memory global state
                live_system_state["current_planes"] = aircraft_list
                live_system_state["last_poll_time"] = time.time()
                
                # Parse planes and look for targets within the radius zone
                for ac in aircraft_list:
                    # [Insert your existing math logic, adsbdb lookups, and DB logs here]
                    pass
                    
            else:
                print(f"⚠️ API Error: Received code {response.status_code}")
                
        except Exception as e:
            print(f"❌ Worker loop encountered exception: {e}")
            
        time.sleep(20)

# --- Lifespan Event Hooks ---
@app.on_event("startup")
def startup_event():
    init_db()
    # Spin up worker loop inside an isolated background thread
    threading.Thread(target=background_polling_worker, daemon=True).start()

# --- REST API Endpoints ---
@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "last_poll_epoch": live_system_state["last_poll_time"],
        "tracked_in_zone": len(live_system_state["current_planes"]),
        "session_total_spotted": live_system_state["session_count"]
    }

@app.get("/api/flights/recent")
def get_recent_flights():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flights_logged ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Real-Time Streaming WebSocket ---
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Instantly push initial snapshot of live environment state upon connect
        await websocket.send_json({"type": "snapshot", "data": live_system_state["current_planes"]})
        while True:
            # Keep socket alive; wait for client messages if any
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)