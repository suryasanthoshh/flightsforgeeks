import React, { useState, useEffect, useRef } from 'react';
import { Plane, Radio, Activity, Navigation, Clock, Hash, AlertTriangle } from 'lucide-react';
import './App.css';

function App() {
  const [planes, setPlanes] = useState([]);
  const [stats, setStats] = useState({ session_count: 0, uptime_seconds: 0 });
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  // Fetch API Stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`http://${window.location.hostname}:8000/api/status`);
        const data = await res.json();
        setStats(data);
      } catch (err) {
        console.error("Failed to fetch stats", err);
      }
    };
    
    fetchStats();
    const interval = setInterval(fetchStats, 10000); // Update stats every 10s
    return () => clearInterval(interval);
  }, []);

  // WebSocket Connection
  useEffect(() => {
    const wsUrl = `ws://${window.location.hostname}:8000/ws/live`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => setIsConnected(true);

    wsRef.current.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "radar_update") {
          setPlanes(payload.data);
        }
      } catch (error) {
        console.error("Error parsing websocket data", error);
      }
    };

    wsRef.current.onclose = () => setIsConnected(false);

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Helper to format uptime
  const formatUptime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  };

  return (
    <div className="dashboard">
      {/* HEADER */}
      <header className="header">
        <div className="logo">
          <Plane className="icon main-icon" />
          <h1>Plane Notifier <span>PRO</span></h1>
        </div>
        <div className={`status-pill ${isConnected ? 'live' : 'offline'}`}>
          <div className="pulse-dot"></div>
          {isConnected ? 'RADAR LIVE' : 'CONNECTING...'}
        </div>
      </header>

      {/* STATS ROW */}
      <div className="stats-grid">
        <div className="stat-card">
          <Radio className="icon stat-icon blue" />
          <div className="stat-info">
            <span className="label">Planes Overhead</span>
            <span className="value">{planes.length}</span>
          </div>
        </div>
        <div className="stat-card">
          <Activity className="icon stat-icon green" />
          <div className="stat-info">
            <span className="label">Session Spotted</span>
            <span className="value">{stats.session_count}</span>
          </div>
        </div>
        <div className="stat-card">
          <Clock className="icon stat-icon purple" />
          <div className="stat-info">
            <span className="label">System Uptime</span>
            <span className="value">{formatUptime(stats.uptime_seconds)}</span>
          </div>
        </div>
      </div>

      {/* RADAR FEED */}
      <div className="feed-container">
        <div className="feed-header">
          <h2>Live Tracking Feed</h2>
        </div>
        
        {planes.length === 0 ? (
          <div className="empty-state">
            <Navigation className="icon empty-icon" />
            <p>Scanning the skies... No aircraft in your radius right now.</p>
          </div>
        ) : (
          <div className="plane-grid">
            {planes.map((plane, idx) => {
              const isEmergency = ["7700", "7600", "7500"].includes(String(plane.squawk));
              
              return (
                <div key={idx} className={`plane-card ${isEmergency ? 'emergency' : ''}`}>
                  {isEmergency && (
                    <div className="emergency-banner">
                      <AlertTriangle size={14} /> EMERGENCY SQUAWK: {plane.squawk}
                    </div>
                  )}
                  
                  <div className="card-top">
                    <div className="flight-id">
                      <h3>{plane.flight?.trim() || "UNKNOWN"}</h3>
                      <span className="squawk"><Hash size={12}/> {plane.squawk || "None"}</span>
                    </div>
                    <div className="hex-badge">{plane.hex}</div>
                  </div>

                  <div className="card-metrics">
                    <div className="metric">
                      <span className="m-label">Altitude</span>
                      <span className="m-val">{plane.alt_baro?.toLocaleString() || 0} <small>ft</small></span>
                    </div>
                    <div className="metric">
                      <span className="m-label">Speed</span>
                      <span className="m-val">{plane.gs || 0} <small>kt</small></span>
                    </div>
                    <div className="metric">
                      <span className="m-label">Distance</span>
                      <span className="m-val">{plane.distance_km?.toFixed(1) || 0} <small>km</small></span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;