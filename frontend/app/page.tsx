"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Activity, 
  Compass, 
  Cpu, 
  Eye, 
  Map, 
  AlertTriangle, 
  ShieldAlert, 
  CheckCircle, 
  Battery, 
  Radio, 
  Navigation,
  RefreshCw,
  Terminal,
  FileText
} from "lucide-react";

interface Telemetry {
  altitude: number;
  speed: number;
  heading: number;
  latitude: number;
  longitude: number;
  battery: number;
  signal: number;
}

interface Detection {
  label: string;
  confidence: number;
  box: [number, number, number, number]; // [x, y, w, h]
}

interface IntrusionAlert {
  severity: string;
  message: string;
  timestamp: string;
}

interface AgentLog {
  agent: string;
  message: string;
}

interface DroneState {
  frame_b64: string;
  telemetry: Telemetry;
  detections: Detection[];
  geomorphology: string;
  operational_interpretation: string;
  intrusion_alerts: IntrusionAlert[];
  agent_logs: AgentLog[];
}

export default function DroMINDDashboard() {
  const [isConnected, setIsConnected] = useState(false);
  const [isFeedActive, setIsFeedActive] = useState(false);
  const [state, setState] = useState<DroneState>({
    frame_b64: "",
    telemetry: {
      altitude: 0.0,
      speed: 0.0,
      heading: 0.0,
      latitude: 37.7749,
      longitude: -122.4194,
      battery: 100,
      signal: 100
    },
    detections: [],
    geomorphology: "Awaiting backend telemetry sync...",
    operational_interpretation: "System standing by. Connect drone stream.",
    intrusion_alerts: [],
    agent_logs: []
  });

  const wsRef = useRef<WebSocket | null>(null);
  const terminalEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll agent logs terminal
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [state.agent_logs]);

  // Connect to FastAPI WebSocket
  const connectWebSocket = () => {
    try {
      console.log("Connecting WebSocket to DroMIND backend...");
      // For Docker compose development environment, backend is on port 8000
      // We check the host to dynamically switch between localhost and current server IP
      const host = window.location.hostname;
      const ws = new WebSocket(`ws://${host}:8000/api/ws?client_type=browser`);

      ws.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connection established with DroMIND backend.");
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.frame_b64) {
          setIsFeedActive(true);
        } else {
          setIsFeedActive(false);
        }
        setState(data);
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsFeedActive(false);
        console.log("WebSocket connection closed. Retrying...");
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error: ", error);
        ws.close();
      };

      wsRef.current = ws;
    } catch (e) {
      console.error("Error setting up WebSocket: ", e);
      setTimeout(connectWebSocket, 3000);
    }
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const hasIntrusions = state.intrusion_alerts && state.intrusion_alerts.length > 0;

  // Custom inline styles for the dashboard grid layout
  const styles = {
    container: {
      padding: "20px",
      maxWidth: "1600px",
      margin: "0 auto",
      display: "flex",
      flexDirection: "column" as const,
      gap: "20px",
      minHeight: "100vh"
    },
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "15px 24px",
      borderRadius: "12px",
      marginBottom: "5px"
    },
    logoSection: {
      display: "flex",
      alignItems: "center",
      gap: "12px"
    },
    logoText: {
      fontSize: "28px",
      fontWeight: "700",
      letterSpacing: "2px",
      background: "linear-gradient(90deg, #00f0ff, #bd00ff)",
      WebkitBackgroundClip: "text",
      WebkitTextFillColor: "transparent",
      textShadow: "0 0 20px rgba(0, 240, 255, 0.2)"
    },
    statusIndicators: {
      display: "flex",
      gap: "16px",
      fontSize: "13px",
      fontWeight: "600",
      letterSpacing: "1px"
    },
    statusBadge: (active: boolean, color: string) => ({
      display: "flex",
      alignItems: "center",
      gap: "6px",
      padding: "6px 12px",
      borderRadius: "6px",
      backgroundColor: active ? `rgba(${color}, 0.1)` : "rgba(255, 255, 255, 0.03)",
      border: `1px solid ${active ? `rgba(${color}, 0.3)` : "rgba(255, 255, 255, 0.05)"}`,
      color: active ? `rgb(${color})` : "var(--color-text-muted)",
      textTransform: "uppercase" as const
    }),
    grid: {
      display: "grid",
      gridTemplateColumns: "1fr 450px",
      gap: "20px",
      flexGrow: 1
    },
    leftCol: {
      display: "flex",
      flexDirection: "column" as const,
      gap: "20px"
    },
    rightCol: {
      display: "flex",
      flexDirection: "column" as const,
      gap: "20px"
    },
    videoViewport: {
      position: "relative" as const,
      width: "100%",
      aspectRatio: "640/480",
      borderRadius: "12px",
      overflow: "hidden",
      border: "1px solid var(--border-muted)"
    },
    streamOverlay: {
      position: "absolute" as const,
      top: 0,
      left: 0,
      width: "100%",
      height: "100%",
      pointerEvents: "none" as const
    },
    telemetryBar: {
      display: "grid",
      gridTemplateColumns: "repeat(6, 1fr)",
      gap: "12px",
      padding: "16px",
      borderRadius: "12px"
    },
    telemetryItem: {
      display: "flex",
      flexDirection: "column" as const,
      alignItems: "center",
      justifyContent: "center",
      gap: "4px",
      padding: "10px",
      borderRadius: "8px",
      backgroundColor: "rgba(255, 255, 255, 0.02)",
      border: "1px solid rgba(255, 255, 255, 0.04)"
    },
    telemetryLabel: {
      fontSize: "11px",
      fontWeight: "600",
      color: "var(--color-text-muted)",
      textTransform: "uppercase" as const,
      letterSpacing: "0.5px"
    },
    telemetryVal: {
      fontSize: "18px",
      fontWeight: "700",
      color: "var(--color-cyan)"
    },
    cardHeader: {
      display: "flex",
      alignItems: "center",
      gap: "10px",
      padding: "12px 16px",
      borderBottom: "1px solid var(--border-muted)",
      fontSize: "14px",
      fontWeight: "700",
      letterSpacing: "1px",
      textTransform: "uppercase" as const,
      color: "var(--color-text-main)"
    },
    cardBody: {
      padding: "16px",
      fontSize: "14px",
      lineHeight: "1.5",
      color: "#cbd5e1"
    },
    agentStatusList: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: "10px",
      padding: "16px"
    },
    agentBadge: (active: boolean, alert = false) => ({
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "12px",
      borderRadius: "8px",
      backgroundColor: alert ? "rgba(255, 42, 95, 0.08)" : "rgba(255, 255, 255, 0.02)",
      border: `1px solid ${
        alert 
          ? "rgba(255, 42, 95, 0.4)" 
          : active 
            ? "rgba(0, 240, 255, 0.3)" 
            : "rgba(255, 255, 255, 0.05)"
      }`
    }),
    agentName: {
      fontSize: "12px",
      fontWeight: "600",
      color: "var(--color-text-main)"
    },
    agentStatusDot: (active: boolean, alert = false) => ({
      width: "8px",
      height: "8px",
      borderRadius: "50%",
      backgroundColor: alert 
        ? "var(--color-red)" 
        : active 
          ? "var(--color-cyan)" 
          : "rgba(255, 255, 255, 0.2)",
      boxShadow: alert 
        ? "0 0 10px var(--color-red)" 
        : active 
          ? "0 0 10px var(--color-cyan)" 
          : "none"
    }),
    terminal: {
      backgroundColor: "rgba(5, 7, 12, 0.85)",
      fontFamily: "var(--font-mono)",
      fontSize: "11px",
      padding: "12px",
      borderRadius: "8px",
      height: "180px",
      overflowY: "auto" as const,
      border: "1px solid rgba(255, 255, 255, 0.03)",
      display: "flex",
      flexDirection: "column" as const,
      gap: "6px"
    },
    terminalLine: (agent: string) => {
      let color = "var(--color-cyan)";
      if (agent === "IntrusionAgent") color = "var(--color-red)";
      if (agent === "GeomorphologyAgent") color = "var(--color-purple)";
      if (agent === "InterpretationAgent") color = "var(--color-amber)";
      return {
        display: "flex",
        gap: "8px",
        color: "#cbd5e1"
      };
    },
    alertBanner: {
      display: "flex",
      alignItems: "center",
      gap: "12px",
      padding: "14px 20px",
      borderRadius: "8px",
      color: "#fff",
      fontSize: "14px",
      fontWeight: "600",
      letterSpacing: "0.5px"
    }
  };

  return (
    <div style={styles.container}>
      {/* 1. Header Bar */}
      <header className="glass-panel hud-border-corners" style={styles.header}>
        <div style={styles.logoSection}>
          <Activity size={24} style={{ color: "var(--color-cyan)", filter: "drop-shadow(0 0 8px rgba(0, 240, 255, 0.5))" }} />
          <h1 className="font-display" style={styles.logoText}>DroMIND</h1>
          <span style={{ fontSize: "11px", color: "var(--color-text-muted)", alignSelf: "flex-end", marginBottom: "4px", fontWeight: 700, fontFamily: "var(--font-mono)" }}>M.A.S. V1.0</span>
        </div>
        
        <div style={styles.statusIndicators}>
          <div style={styles.statusBadge(isConnected, "0, 240, 255")}>
            <Radio size={14} className={isConnected ? "blink" : ""} />
            <span>Server: {isConnected ? "Online" : "Connecting"}</span>
          </div>
          <div style={styles.statusBadge(isFeedActive, "0, 230, 118")}>
            <Eye size={14} className={isFeedActive ? "blink" : ""} />
            <span>Feed: {isFeedActive ? "Active" : "Offline"}</span>
          </div>
          <div style={styles.statusBadge(hasIntrusions, "255, 42, 95")} className={hasIntrusions ? "pulse-alert-red" : ""}>
            <ShieldAlert size={14} />
            <span style={{ color: hasIntrusions ? "#fff" : "inherit" }}>
              Perimeter: {hasIntrusions ? "BREACHED" : "NOMINAL"}
            </span>
          </div>
        </div>
        <div className="corner-bottom-left" style={{ bottom: "-1px", left: "-1px", borderWidth: "0 0 2px 2px" }} />
        <div className="corner-bottom-right" style={{ bottom: "-1px", right: "-1px", borderWidth: "0 2px 2px 0" }} />
      </header>

      {/* 2. Main Dashboard Grid */}
      <main style={styles.grid}>
        
        {/* Left Column: Drone Live Camera & Overlay */}
        <section style={styles.leftCol}>
          <div className="glass-panel animate-scan" style={styles.videoViewport}>
            {state.frame_b64 ? (
              // Display base64 video frame
              <img 
                src={state.frame_b64.startsWith("data:") ? state.frame_b64 : `data:image/jpeg;base64,${state.frame_b64}`} 
                alt="Drone Live Stream"
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            ) : (
              // Standby display when no drone stream is active
              <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "15px", backgroundColor: "#07090e" }}>
                <Cpu size={48} className="blink" style={{ color: "var(--color-cyan)", filter: "drop-shadow(0 0 10px rgba(0, 240, 255, 0.4))" }} />
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <p className="font-display" style={{ fontSize: "18px", color: "var(--color-text-main)", letterSpacing: "1px", fontWeight: 600 }}>AWAITING DRONE LIVE STREAM</p>
                  <p style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>Start the mock_drone.py script to initialize camera feed</p>
                </div>
              </div>
            )}

            {/* Drone Telemetry HUD Overlay (SVG) */}
            <svg viewBox="0 0 640 480" style={styles.streamOverlay}>
              {/* Center HUD Reticle */}
              <circle cx="320" cy="240" r="40" fill="none" stroke="rgba(0, 240, 255, 0.3)" strokeWidth="1" />
              <line x1="320" y1="180" x2="320" y2="200" stroke="rgba(0, 240, 255, 0.3)" strokeWidth="1" />
              <line x1="320" y1="280" x2="320" y2="300" stroke="rgba(0, 240, 255, 0.3)" strokeWidth="1" />
              <line x1="260" y1="240" x2="280" y2="240" stroke="rgba(0, 240, 255, 0.3)" strokeWidth="1" />
              <line x1="360" y1="240" x2="380" y2="240" stroke="rgba(0, 240, 255, 0.3)" strokeWidth="1" />
              
              {/* Compass HUD scale top */}
              <rect x="220" y="20" width="200" height="20" fill="rgba(0, 0, 0, 0.4)" stroke="rgba(0, 240, 255, 0.2)" strokeWidth="1" />
              <text x="320" y="34" fill="var(--color-cyan)" fontSize="10" fontFamily="Orbitron" textAnchor="middle">
                HDG: {state.telemetry.heading.toFixed(0)}°
              </text>

              {/* Geofence Boundary: Restricted Zone Alpha */}
              {/* Draw restricted perimeter box matching backend logic (X: 250 to 500, Y: 100 to 400) */}
              <rect 
                x="250" 
                y="100" 
                width="250" 
                height="300" 
                fill="none" 
                stroke={hasIntrusions ? "rgba(255, 42, 95, 0.6)" : "rgba(255, 184, 0, 0.4)"} 
                strokeWidth="2" 
                strokeDasharray="6,4"
              />
              <rect 
                x="250" 
                y="80" 
                width="160" 
                height="20" 
                fill={hasIntrusions ? "rgba(255, 42, 95, 0.8)" : "rgba(255, 184, 0, 0.6)"} 
              />
              <text x="256" y="94" fill="#fff" fontSize="10" fontFamily="Orbitron" fontWeight="bold">
                RESTRICTED ZONE ALPHA
              </text>

              {/* Draw Detections Bounding Boxes */}
              {isFeedActive && state.detections && state.detections.map((det, index) => {
                const [x, y, w, h] = det.box;
                // Determine if detection is inside the zone (checking center of bounding box)
                const cx = x + w / 2;
                const cy = y + h / 2;
                const isInZone = cx >= 250 && cx <= 500 && cy >= 100 && cy <= 400;
                
                const boxStroke = isInZone ? "var(--color-red)" : (det.label === "person" ? "var(--color-amber)" : "var(--color-cyan)");
                
                return (
                  <g key={index}>
                    {/* Bounding Box rectangle */}
                    <rect 
                      x={x} 
                      y={y} 
                      width={w} 
                      height={h} 
                      fill="none" 
                      stroke={boxStroke} 
                      strokeWidth="2.5" 
                      style={{ filter: `drop-shadow(0 0 4px ${boxStroke})` }}
                    />
                    {/* Label Badge */}
                    <rect 
                      x={x} 
                      y={y - 18} 
                      width={det.label.length * 8 + 42} 
                      height="18" 
                      fill={boxStroke} 
                    />
                    <text 
                      x={x + 4} 
                      y={y - 5} 
                      fill="#000" 
                      fontSize="10" 
                      fontFamily="Orbitron" 
                      fontWeight="bold"
                    >
                      {det.label.toUpperCase()} {(det.confidence * 100).toFixed(0)}%
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Telemetry Display Grid */}
          <div className="glass-panel" style={styles.telemetryBar}>
            <div style={styles.telemetryItem}>
              <div style={styles.telemetryLabel}>Altitude</div>
              <div className="font-mono" style={styles.telemetryVal}>{state.telemetry.altitude.toFixed(1)} m</div>
            </div>
            <div style={styles.telemetryItem}>
              <div style={styles.telemetryLabel}>Ground Speed</div>
              <div className="font-mono" style={styles.telemetryVal}>{state.telemetry.speed.toFixed(1)} m/s</div>
            </div>
            <div style={styles.telemetryItem}>
              <div style={styles.telemetryLabel}>Coordinates</div>
              <div className="font-mono" style={{ ...styles.telemetryVal, fontSize: "13px" }}>
                {state.telemetry.latitude.toFixed(5)}, {state.telemetry.longitude.toFixed(5)}
              </div>
            </div>
            <div style={styles.telemetryItem}>
              <div style={styles.telemetryLabel}>Battery</div>
              <div className="font-mono" style={{ ...styles.telemetryVal, color: state.telemetry.battery < 25 ? "var(--color-red)" : "var(--color-green)", display: "flex", alignItems: "center", gap: "6px" }}>
                <Battery size={16} />
                {state.telemetry.battery}%
              </div>
            </div>
            <div style={styles.telemetryItem}>
              <div style={styles.telemetryLabel}>Heading</div>
              <div className="font-mono" style={{ ...styles.telemetryVal, display: "flex", alignItems: "center", gap: "6px" }}>
                <Compass size={16} />
                {state.telemetry.heading.toFixed(0)}°
              </div>
            </div>
            <div style={styles.telemetryItem}>
              <div style={styles.telemetryLabel}>Signal</div>
              <div className="font-mono" style={styles.telemetryVal}>{state.telemetry.signal}%</div>
            </div>
          </div>
        </section>

        {/* Right Column: Multi-Agent Hub and Log Panels */}
        <section style={styles.rightCol}>
          
          {/* Agent Status Panel */}
          <div className="glass-panel" style={{ borderRadius: "12px" }}>
            <div style={styles.cardHeader}>
              <Cpu size={18} style={{ color: "var(--color-cyan)" }} />
              <span className="font-display">Agent Orchestration Status</span>
            </div>
            <div style={styles.agentStatusList}>
              <div style={styles.agentBadge(isFeedActive)}>
                <span style={styles.agentName}>Detection Agent</span>
                <span style={styles.agentStatusDot(isFeedActive)} />
              </div>
              <div style={styles.agentBadge(isFeedActive)}>
                <span style={styles.agentName}>Geomorphology Agent</span>
                <span style={styles.agentStatusDot(isFeedActive)} />
              </div>
              <div style={styles.agentBadge(isFeedActive)}>
                <span style={styles.agentName}>Interpretation Agent</span>
                <span style={styles.agentStatusDot(isFeedActive)} />
              </div>
              <div style={styles.agentBadge(isFeedActive, hasIntrusions)}>
                <span style={styles.agentName}>Intrusion Agent</span>
                <span style={styles.agentStatusDot(isFeedActive, hasIntrusions)} />
              </div>
            </div>
          </div>

          {/* Geomorphology Card */}
          <div className="glass-panel" style={{ borderRadius: "12px" }}>
            <div style={styles.cardHeader}>
              <Map size={18} style={{ color: "var(--color-purple)" }} />
              <span className="font-display">Geomorphology & Terrain Analysis</span>
            </div>
            <div style={styles.cardBody}>
              <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                <FileText size={18} style={{ color: "var(--color-purple)", marginTop: "3px", flexShrink: 0 }} />
                <p style={{ fontFamily: "var(--font-sans)", fontSize: "13px" }}>
                  {state.geomorphology}
                </p>
              </div>
            </div>
          </div>

          {/* Operational Interpretation Card */}
          <div className="glass-panel" style={{ borderRadius: "12px" }}>
            <div style={styles.cardHeader}>
              <Navigation size={18} style={{ color: "var(--color-amber)" }} />
              <span className="font-display">Operational Recommendations</span>
            </div>
            <div style={styles.cardBody}>
              <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                <CheckCircle size={18} style={{ color: "var(--color-green)", marginTop: "3px", flexShrink: 0 }} />
                <p style={{ fontFamily: "var(--font-sans)", fontSize: "13px" }}>
                  {state.operational_interpretation}
                </p>
              </div>
            </div>
          </div>

          {/* Live Agent Orchestrator Log Terminal */}
          <div className="glass-panel" style={{ borderRadius: "12px", flexGrow: 1, display: "flex", flexDirection: "column" }}>
            <div style={styles.cardHeader}>
              <Terminal size={18} style={{ color: "var(--color-cyan)" }} />
              <span className="font-display">LangGraph Execution Console</span>
            </div>
            <div style={{ padding: "16px", flexGrow: 1, display: "flex", flexDirection: "column" }}>
              <div style={styles.terminal}>
                {state.agent_logs.length === 0 ? (
                  <div style={{ color: "var(--color-text-muted)", fontStyle: "italic" }}>
                    Console idle. Waiting for active frame streaming...
                  </div>
                ) : (
                  state.agent_logs.map((log, index) => {
                    let agentColor = "var(--color-cyan)";
                    if (log.agent === "IntrusionAgent") agentColor = "var(--color-red)";
                    if (log.agent === "GeomorphologyAgent") agentColor = "var(--color-purple)";
                    if (log.agent === "InterpretationAgent") agentColor = "var(--color-amber)";
                    
                    return (
                      <div key={index} style={styles.terminalLine(log.agent)}>
                        <span style={{ color: agentColor, fontWeight: "bold" }}>[{log.agent}]</span>
                        <span>{log.message}</span>
                      </div>
                    );
                  })
                )}
                <div ref={terminalEndRef} />
              </div>
            </div>
          </div>

        </section>
      </main>

      {/* 3. Bottom Banner Alert System */}
      {hasIntrusions && (
        <section 
          className="pulse-alert-red" 
          style={{
            ...styles.alertBanner,
            backgroundColor: "rgba(255, 42, 95, 0.95)",
            boxShadow: "0 0 30px rgba(255, 42, 95, 0.4)",
            border: "1px solid var(--color-red)"
          }}
        >
          <AlertTriangle size={24} style={{ color: "#fff", filter: "drop-shadow(0 0 8px #fff)" }} />
          <div>
            <div style={{ fontSize: "14px", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "1px" }}>
              SECURITY BREACH DETECTED
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              {state.intrusion_alerts[0]?.message} (Logged at {state.intrusion_alerts[0]?.timestamp} UTC)
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
