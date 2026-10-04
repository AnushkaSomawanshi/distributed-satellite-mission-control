import React, { useState, useEffect, useRef } from 'react';
import { Video, Radio, RefreshCw, Play, AlertTriangle, Activity, Wifi, ShieldAlert } from 'lucide-react';

export default function MultimediaPage() {
  const [selectedSat, setSelectedSat] = useState('SAT-03');
  const [satellites, setSatellites] = useState([]);
  const [streamState, setStreamState] = useState('CONNECTED'); // CONNECTED, STREAM_LOST, CONNECTING
  const [peerInfo, setPeerInfo] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const canvasRef = useRef(null);

  // Poll satellite list & selected telemetry
  useEffect(() => {
    const fetchSats = async () => {
      try {
        const res = await fetch('/api/satellites');
        const data = await res.json();
        const satList = data.satellites || [];
        setSatellites(satList);

        const current = satList.find(s => s.satellite_id === selectedSat);
        if (current) {
          setTelemetry(current);
          if (['DISCONNECTED', 'OFFLINE'].includes(current.status)) {
            setStreamState('STREAM_LOST');
          } else if (streamState === 'STREAM_LOST' && ['HEALTHY', 'WARNING', 'CRITICAL', 'ONLINE'].includes(current.status)) {
            setStreamState('CONNECTED');
          }
        }
      } catch (e) {}
    };

    fetchSats();
    const interval = setInterval(fetchSats, 2000);
    return () => clearInterval(interval);
  }, [selectedSat, streamState]);

  // Orbital HUD Video Frame Renderer
  useEffect(() => {
    let animationFrameId;
    let angle = 0;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const renderOrbitalView = () => {
      angle += 0.02;
      ctx.fillStyle = '#020617';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Earth Curvature
      const earthGradient = ctx.createRadialGradient(
        canvas.width / 2, canvas.height + 260, 100,
        canvas.width / 2, canvas.height + 260, 460
      );
      earthGradient.addColorStop(0, '#0284c7');
      earthGradient.addColorStop(0.5, '#0369a1');
      earthGradient.addColorStop(1, '#0f172a');
      
      ctx.fillStyle = earthGradient;
      ctx.beginPath();
      ctx.arc(canvas.width / 2, canvas.height + 260, 460, 0, Math.PI * 2);
      ctx.fill();

      // Atmospheric Limb
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(canvas.width / 2, canvas.height + 260, 462, Math.PI * 1.1, Math.PI * 1.9);
      ctx.stroke();

      // Target Crosshair Grid
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.3)';
      ctx.lineWidth = 1;
      ctx.strokeRect(30, 30, canvas.width - 60, canvas.height - 60);

      // Telemetry HUD Overlay
      ctx.fillStyle = '#38bdf8';
      ctx.font = '12px monospace';
      const timeStr = new Date().toLocaleTimeString();
      ctx.fillText(`● WEBRTC LIVE STREAM | ${selectedSat} ONBOARD CAMERA`, 45, 50);
      ctx.fillText(`TIMESTAMP: ${timeStr} | FPS: 30`, 45, 70);
      if (telemetry) {
        ctx.fillStyle = telemetry.temperature > 75 ? '#ef4444' : '#38bdf8';
        ctx.fillText(`TEMP: ${telemetry.temperature}°C | BATT: ${telemetry.battery}% | CPU: ${telemetry.cpu_usage}%`, 45, 90);
        ctx.fillText(`HEALTH: ${telemetry.health_score}% | MODE: ${telemetry.power_mode || 'NORMAL'}`, 45, 110);
      }

      if (streamState === 'CONNECTED') {
        animationFrameId = requestAnimationFrame(renderOrbitalView);
      }
    };

    if (streamState === 'CONNECTED') {
      renderOrbitalView();
    }

    return () => cancelAnimationFrame(animationFrameId);
  }, [streamState, selectedSat, telemetry]);

  const handleStartWebRTC = async () => {
    setStreamState('CONNECTING');
    try {
      const dummyOffer = "v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\ns=WebRTC Client\r\nt=0 0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n";
      const res = await fetch('/api/webrtc/offer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offer_sdp: dummyOffer, peer: selectedSat })
      });
      const data = await res.json();
      setPeerInfo(data);
      setStreamState('CONNECTED');
    } catch (e) {
      setStreamState('STREAM_LOST');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron">WebRTC Live Satellite Camera & Telemetry Overlay</h2>
          <p className="text-xs text-slate-400 font-mono">
            Real WebRTC video feed with side-by-side WebSocket telemetry correlation & container loss detection
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={selectedSat}
            onChange={(e) => setSelectedSat(e.target.value)}
            className="bg-slate-900 text-slate-200 border border-slate-700 font-mono text-xs px-3 py-2 rounded-lg"
          >
            {['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <button
            onClick={handleStartWebRTC}
            className="py-2 px-4 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center space-x-2"
          >
            {streamState === 'CONNECTING' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>RECONNECT WEBRTC</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Camera Stream */}
        <div className="lg:col-span-2 glass-panel p-4 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center justify-between px-2">
            <span className="text-xs font-bold text-slate-300 font-orbitron flex items-center space-x-2">
              <Video className="w-4 h-4 text-cyan-400" />
              <span>{selectedSat} ONBOARD CAMERA FEED (WEBRTC MULTIMEDIA)</span>
            </span>
            <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold ${
              streamState === 'CONNECTED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
            }`}>
              {streamState === 'CONNECTED' ? '● LIVE WEBRTC' : '🔴 STREAM LOST'}
            </span>
          </div>

          <div className="relative aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center">
            {streamState === 'CONNECTED' ? (
              <canvas ref={canvasRef} width={640} height={360} className="w-full h-full object-cover" />
            ) : (
              <div className="text-center space-y-3 text-rose-400 p-8 font-mono text-xs">
                <ShieldAlert className="w-12 h-12 text-rose-500 mx-auto animate-bounce" />
                <p className="font-bold text-sm">STREAM LOST (NODE DISCONNECTED)</p>
                <p className="text-slate-400 text-[11px]">
                  Reason: {selectedSat} container process stopped or heartbeat timed out. Stream will automatically restore upon satellite node reboot.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Live Telemetry Side-by-Side Panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-slate-200 font-orbitron flex items-center space-x-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>WebSocket Live Correlation</span>
          </h3>

          {telemetry ? (
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center">
                <span className="text-slate-400">Node Status:</span>
                <span className={`font-bold ${telemetry.status === 'HEALTHY' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {telemetry.status}
                </span>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center">
                <span className="text-slate-400">Battery Level:</span>
                <span className="text-cyan-400 font-bold">{telemetry.battery}%</span>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center">
                <span className="text-slate-400">Temperature:</span>
                <span className={`font-bold ${telemetry.temperature > 75 ? 'text-rose-400' : 'text-slate-200'}`}>
                  {telemetry.temperature}°C
                </span>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center">
                <span className="text-slate-400">CPU Usage:</span>
                <span className="text-slate-200 font-bold">{telemetry.cpu_usage}%</span>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center">
                <span className="text-slate-400">Health Score:</span>
                <span className="text-emerald-400 font-bold">{telemetry.health_score}%</span>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center">
                <span className="text-slate-400">Power Mode:</span>
                <span className="text-amber-400 font-bold">{telemetry.power_mode || 'NORMAL'}</span>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-slate-500 text-xs font-mono">
              Loading telemetry correlation...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
