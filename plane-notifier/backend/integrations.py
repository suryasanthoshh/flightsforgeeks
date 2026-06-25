import os
import requests
from functools import lru_cache

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHATS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")

@lru_cache(maxsize=1000)
def lookup_aircraft(hex_code: str, callsign: str) -> dict:
    try:
        url = f"https://api.adsbdb.com/v0/aircraft/{hex_code}?callsign={callsign}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"ADSBDB lookup failed for {hex_code}: {e}")
    return {}

def get_flight_phase(vertical_rate: int) -> str:
    if vertical_rate is None: return "Cruising ✈️"
    if vertical_rate > 500: return "Climbing 📈"
    elif vertical_rate < -500: return "Descending 📉"
    return "Cruising ✈️"

def send_telegram_alert(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHATS[0]:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHATS:
        try:
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
        except Exception as e:
            print(f"Telegram failed: {e}")

def format_alert(plane: dict, meta: dict, badges: list, is_new: bool) -> str:
    reg = meta.get("response", {}).get("aircraft", {}).get("registration", "Unknown")
    type_code = meta.get("response", {}).get("aircraft", {}).get("type", "Unknown")
    
    header = "⭐ <b>NEW DISCOVERY</b>\n" if is_new else "✈️ <b>Aircraft Spotted</b>\n"
    badge_str = " ".join(badges) + "\n" if badges else ""
    
    msg = f"{header}{badge_str}"
    msg += f"<b>Callsign:</b> {plane.get('flight', 'N/A').strip()}\n"
    msg += f"<b>Reg:</b> {reg} | <b>Type:</b> {type_code}\n"
    msg += f"<b>Alt:</b> {plane.get('alt_baro', 0)} ft | <b>Speed:</b> {plane.get('gs', 0)} kt\n"
    msg += f"<b>Phase:</b> {get_flight_phase(plane.get('baro_rate', 0))}\n"
    msg += f"<b>Dist:</b> {plane.get('distance_km', 0):.2f} km\n"
    
    if reg != "Unknown":
        msg += f"<a href='https://www.jetphotos.com/registration/{reg}'>View JetPhotos</a>"
    return msg