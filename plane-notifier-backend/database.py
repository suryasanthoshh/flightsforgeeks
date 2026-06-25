import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "data/plane_notifier.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Flights Logged Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flights_logged (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp_utc TEXT,
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
    )""")
    
    # 2. Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    
    # 3. Watchlist Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        watch_type TEXT,
        value TEXT,
        added_by TEXT,
        added_at TEXT
    )""")
    
    # Populate Default Settings if empty
    defaults = {
        "alert_radius": "3.0",
        "units": "metric",
        "quiet_hours": "off",
        "heartbeat": "on",
        "cooldown_minutes": "15"
    }
    for key, val in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
        
    conn.commit()
    conn.close()

def get_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}