import database as db

def check_gamification(altitude_ft: int, speed_kt: int) -> list:
    badges = []
    with db.get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM flights_logged").fetchone()[0]
        if total > 0 and total % 100 == 0:
            badges.append(f"🏆 Milestone: {total}th Flight!")

        records = dict(conn.execute("SELECT key, value FROM records").fetchall())
        lowest_alt = records.get("lowest_alt", float('inf'))
        fastest_speed = records.get("fastest_speed", 0)

        if altitude_ft and altitude_ft < lowest_alt and altitude_ft > 0:
            badges.append("⬇️ NEW RECORD: Lowest Altitude!")
            conn.execute("INSERT OR REPLACE INTO records (key, value) VALUES ('lowest_alt', ?)", (altitude_ft,))
            
        if speed_kt and speed_kt > fastest_speed:
            badges.append("⚡ NEW RECORD: Fastest Speed!")
            conn.execute("INSERT OR REPLACE INTO records (key, value) VALUES ('fastest_speed', ?)", (speed_kt,))
        conn.commit()
    return badges

def is_first_sighting(hex_code: str) -> bool:
    with db.get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM flights_logged WHERE hex = ?", (hex_code,)).fetchone()[0]
    return count == 0

def check_route_anomaly(callsign: str, alt: int, heading: int) -> list:
    if not callsign: return []
    with db.get_db() as conn:
        rows = conn.execute("SELECT altitude_ft, heading_deg FROM flights_logged WHERE callsign = ? ORDER BY id DESC LIMIT 100", (callsign,)).fetchall()
    
    if not rows or len(rows) < 5: return []
    
    avg_alt = sum(r['altitude_ft'] for r in rows if r['altitude_ft']) / len(rows)
    avg_hdg = sum(r['heading_deg'] for r in rows if r['heading_deg']) / len(rows)
    
    anomalies = []
    if alt and abs(alt - avg_alt) > (0.30 * avg_alt):
        anomalies.append("⚠️ Altitude Anomaly (>30% deviation)")
    if heading and abs(heading - avg_hdg) > (0.30 * avg_hdg):
        anomalies.append("⚠️ Heading Anomaly (>30% deviation)")
    return anomalies