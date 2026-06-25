import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "./data/plane_notifier.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flights_logged (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                date_local TEXT,
                hex TEXT,
                registration TEXT,
                callsign TEXT,
                airline TEXT,
                aircraft_type TEXT,
                type_code TEXT,
                altitude_ft INTEGER,
                speed_kt INTEGER,
                heading_deg INTEGER,
                vertical_rate INTEGER,
                distance_km REAL,
                squawk TEXT,
                route_origin TEXT,
                route_destination TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                value TEXT,
                added_by TEXT,
                added_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                key TEXT PRIMARY KEY,
                value REAL
            )
        """)
        
        # Default settings
        defaults = {
            "alert_radius": "5.0",
            "units": "metric",
            "quiet_hours": "23-07",
            "heartbeat": "1",
            "cooldown_minutes": "15"
        }
        for k, v in defaults.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()

def get_settings():
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}

def update_settings(updates: dict):
    with get_db() as conn:
        for k, v in updates.items():
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
        conn.commit()

def log_flight(data: dict):
    with get_db() as conn:
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        conn.execute(f"INSERT INTO flights_logged ({cols}) VALUES ({placeholders})", tuple(data.values()))
        conn.commit()