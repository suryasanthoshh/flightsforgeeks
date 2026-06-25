import os
import time
import math
import threading
from datetime import datetime, timezone
import requests
import database as db
import integrations as ig
import analytics as an

HOME_LAT = float(os.getenv("HOME_LAT", "0.0"))
HOME_LON = float(os.getenv("HOME_LON", "0.0"))
EMERGENCY_SQUAWKS = ["7700", "7600", "7500"]

# Shared state for WebSockets
shared_data_lock = threading.Lock()
live_radar_state = []
uptime_start = datetime.utcnow()
session_count = 0

cooldowns = {}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def poll_loop():
    global session_count, live_radar_state
    print("Background worker started.")
    
    while True:
        settings = db.get_settings()
        radius = float(settings.get("alert_radius", 5.0))
        cooldown_mins = float(settings.get("cooldown_minutes", 15.0))
        
        try:
            url = f"https://api.airplanes.live/v2/point/{HOME_LAT}/{HOME_LON}/{radius * 2}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                ac_list = data.get("ac", [])
                
                current_radar = []
                now = datetime.now(timezone.utc).timestamp()
                
                for plane in ac_list:
                    lat, lon = plane.get("lat"), plane.get("lon")
                    if not lat or not lon: continue
                    
                    dist = haversine(HOME_LAT, HOME_LON, lat, lon)
                    plane['distance_km'] = dist
                    current_radar.append(plane)
                    
                    hex_code = plane.get("hex")
                    squawk = str(plane.get("squawk", ""))
                    
                    is_emergency = squawk in EMERGENCY_SQUAWKS
                    if dist <= radius or is_emergency:
                        last_seen = cooldowns.get(hex_code, 0)
                        
                        # Process if emergency OR cooldown expired
                        if is_emergency or (now - last_seen > (cooldown_mins * 60)):
                            cooldowns[hex_code] = now
                            session_count += 1
                            
                            callsign = plane.get("flight", "").strip()
                            meta = ig.lookup_aircraft(hex_code, callsign)
                            
                            is_new = an.is_first_sighting(hex_code)
                            badges = an.check_gamification(plane.get("alt_baro"), plane.get("gs"))
                            anomalies = an.check_route_anomaly(callsign, plane.get("alt_baro"), plane.get("track"))
                            badges.extend(anomalies)
                            
                            if is_emergency: badges.append(f"🚨 EMERGENCY SQUAWK: {squawk}")
                            
                            # Save to DB
                            db.log_flight({
                                "timestamp_utc": datetime.utcnow().isoformat(),
                                "hex": hex_code,
                                "callsign": callsign,
                                "altitude_ft": plane.get("alt_baro"),
                                "speed_kt": plane.get("gs"),
                                "heading_deg": plane.get("track"),
                                "vertical_rate": plane.get("baro_rate"),
                                "distance_km": dist,
                                "squawk": squawk
                            })
                            
                            alert_msg = ig.format_alert(plane, meta, badges, is_new)
                            ig.send_telegram_alert(alert_msg)
                            print(f"Logged & Alerted: {hex_code}")
                
                # Update shared state
                with shared_data_lock:
                    live_radar_state = current_radar
                    
        except Exception as e:
            print(f"Worker Loop Error: {e}")
            
        time.sleep(20)

def start_worker():
    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()