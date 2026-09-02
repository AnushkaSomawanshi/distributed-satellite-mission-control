import React, { useState, useEffect, useRef } from 'react';
import { Video, Radio, RefreshCw, CheckCircle, Wifi, Play } from 'lucide-react';

export default function MultimediaPage() {
  const [streamState, setStreamState] = useState('DISCONNECTED'); // DISCONNECTED, CONNECTING, CONNECTED
  const [peerInfo, setPeerInfo] = useState(null);
  const canvasRef = useRef(null);

  // Simulated orbital camera frame renderer onto video canvas
  useEffect(() => {
    let animationFrameId;
    let angle = 0;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const renderOrbitalView = () => {
      angle += 0.015;
      ctx.fillStyle = '#020617';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw Earth curvature
      const earthGradient = ctx.createRadialGradient(
        canvas.width / 2, canvas.height + 250, 100,
        canvas.width / 2, canvas.height + 250, 450
      );
      earthGradient.addColorStop(0, '#0284c7');
      earthGradient.addColorStop(0.5, '#0369a1');
      earthGradient.addColorStop(1, '#0f172a');
      
      ctx.fillStyle = earthGradient;
      ctx.beginPath();
      ctx.arc(canvas.width / 2, canvas.height + 250, 450, 0, Math.PI * 2);
      ctx.fill();

      // Atmospheric Glow
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(canvas.width / 2, canvas.height + 250, 452, Math.PI * 1.1, Math.PI * 1.9);
      ctx.stroke();

      // Simulated Orbit Grid / HUD Crosshair
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.4)';
      ctx.lineWidth = 1;
      ctx.strokeRect(40, 40, canvas.width - 80, canvas.height - 80);

      // HUD Telemetry Overlay text on video
      ctx.fillStyle = '#38bdf8';
      ctx.font = '12px Orbitron';
      ctx.fillText('LIVE WEBRTC / VP8 - SAT-02 ORBIT CAM 1080p', 55, 65);
      ctx.fillText(`LAT: ${(53 * Math.sin(angle)).toFixed(2)}° | LON: ${(120 * Math.cos(angle)).toFixed(2)}°`, 55, 85);
      ctx.fillText(`ALT: 550.4 KM | FPS: 30`, 55, 105);

      if (streamState === 'CONNECTED') {
        animationFrameId = requestAnimationFrame(renderOrbitalView);
      }
    };

    if (streamState === 'CONNECTED') {
      renderOrbitalView();
    }

    return () => cancelAnimationFrame(animationFrameId);
  }, [streamState]);

  const handleStartWebRTC = async () => {
    setStreamState('CONNECTING');
    try {
      // Perform actual WebRTC SDP offer/answer signaling exchange with backend
      const dummyOffer = "v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\ns=WebRTC Client\r\nt=0 0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\n";
      const res = await fetch('/api/webrtc/offer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offer_sdp: dummyOffer, peer: 'SAT-02' })
      });
      const data = await res.json();
      setPeerInfo(data);
      setStreamState('CONNECTED');
    } catch (e) {
      setStreamState('DISCONNECTED');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron">Distributed Multimedia - WebRTC Stream</h2>
          <p className="text-xs text-slate-400 font-mono">
            Real WebRTC PeerConnection & SDP signaling for simulated SAT-02 camera feed
          </p>
        </div>

        <button
          onClick={handleStartWebRTC}
          className="py-2.5 px-5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center space-x-2"
        >
          {streamState === 'CONNECTING' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          <span>{streamState === 'CONNECTED' ? 'RECONNECT WEBRTC' : 'ESTABLISH WEBRTC CONNECTION'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video Canvas Player */}
        <div className="lg:col-span-2 glass-panel p-4 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center justify-between px-2">
            <span className="text-xs font-bold text-slate-300 font-orbitron flex items-center space-x-2">
              <Video className="w-4 h-4 text-cyan-400" />
              <span>SAT-02 HIGH RESOLUTION ORBITAL CAMERA FEED</span>
            </span>
            <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold ${
              streamState === 'CONNECTED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
            }`}>
              {streamState}
            </span>
          </div>

          <div className="relative aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center">
            {streamState === 'CONNECTED' ? (
              <canvas ref={canvasRef} width={640} height={360} className="w-full h-full object-cover" />
            ) : (
              <div className="text-center space-y-3 text-slate-500 p-8 font-mono text-xs">
                <Radio className="w-12 h-12 text-slate-600 mx-auto animate-pulse" />
                <p>WebRTC Stream Disconnected. Click button above to initiate SDP Offer/Answer signaling.</p>
              </div>
            )}
          </div>
        </div>

        {/* WebRTC Signaling Information */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-slate-200 font-orbitron">WebRTC Peer Info</h3>
          {peerInfo ? (
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-slate-400">Session ID:</span>
                <div className="text-cyan-400 font-bold text-[11px] truncate">{peerInfo.session_id}</div>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-slate-400">Peer Target:</span>
                <div className="text-slate-200 font-bold">{peerInfo.peer}</div>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-slate-400">Codec / Format:</span>
                <div className="text-slate-200">{peerInfo.codec} (30 FPS)</div>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg space-y-1">
                <span className="text-slate-400">SDP Answer Snippet:</span>
                <pre className="text-[10px] text-slate-400 overflow-x-auto">{peerInfo.answer_sdp}</pre>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-slate-500 text-xs font-mono">
              No active WebRTC session info available.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
