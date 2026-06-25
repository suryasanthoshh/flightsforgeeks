import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import database as db
import worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    worker.start_worker()
    yield

app = FastAPI(title="Plane Notifier Pro", lifespan=lifespan)

class SettingsUpdate(BaseModel):
    settings: dict

@app.get("/api/status")
def get_status():
    uptime = worker.datetime.utcnow() - worker.uptime_start
    return {
        "status": "running",
        "uptime_seconds": uptime.total_seconds(),
        "session_count": worker.session_count
    }

@app.get("/api/flights/recent")
def get_recent_flights():
    with db.get_db() as conn:
        rows = conn.execute("SELECT * FROM flights_logged ORDER BY id DESC LIMIT 50").fetchall()
    return [dict(r) for r in rows]

@app.get("/api/settings")
def get_settings():
    return db.get_settings()

@app.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    db.update_settings(payload.settings)
    return {"status": "success", "settings": db.get_settings()}

@app.get("/api/stats/today")
def get_stats_today():
    today = worker.datetime.utcnow().strftime("%Y-%m-%d")
    with db.get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM flights_logged WHERE timestamp_utc LIKE ?", (f"{today}%",)).fetchone()[0]
        airlines = conn.execute("SELECT COUNT(DISTINCT airline) FROM flights_logged WHERE timestamp_utc LIKE ? AND airline IS NOT NULL", (f"{today}%",)).fetchone()[0]
    return {"today_count": count, "unique_airlines": airlines}

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            with worker.shared_data_lock:
                current_data = list(worker.live_radar_state)
            await websocket.send_json({"type": "radar_update", "data": current_data})
            await asyncio.sleep(20)
    except WebSocketDisconnect:
        print("WebSocket disconnected")