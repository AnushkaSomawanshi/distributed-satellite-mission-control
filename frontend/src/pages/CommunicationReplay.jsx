import React, { useState } from 'react';
import { History, Play, Pause, RotateCcw, ArrowRight } from 'lucide-react';

export default function CommunicationReplay() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  const sampleTimelineEvents = [
    { time: '10:31:01', source: 'SAT-01', dest: 'Mission Control', protocol: 'RABBITMQ', desc: 'TELEMETRY_PUBLISHED: Battery 98%, Temp 24°C' },
    { time: '10:31:02', source: 'Mission Control', dest: 'SAT-03', protocol: 'gRPC', desc: 'RPC_CALL: GetHealth() -> Latency 14ms (SUCCESS)' },
    { time: '10:31:04', source: 'SAT-01', dest: 'SAT-04', protocol: 'P2P Direct', desc: 'P2P_MESSAGE: Cross-link Orbital Handshake (ACK)' },
    { time: '10:31:05', source: 'SAT-02', dest: 'Dashboard', protocol: 'WebSocket', desc: 'STREAM_FRAME: Telemetry batch delivered over WS' },
    { time: '10:31:06', source: 'SAT-02', dest: 'Ground Station', protocol: 'WebRTC', desc: 'WEBRTC_FRAME: Orbital camera stream active (VP8/1080p)' }
  ];

  const handlePlayToggle = () => {
    if (!isPlaying) {
      setIsPlaying(true);
      const interval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= sampleTimelineEvents.length - 1) {
            clearInterval(interval);
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1500);
    } else {
      setIsPlaying(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron">Communication Event Replay</h2>
          <p className="text-xs text-slate-400 font-mono">
            Historical message playback timeline (Foundation for FA-2 Logical Clock visualization)
          </p>
        </div>

        <div className="flex space-x-2">
          <button
            onClick={handlePlayToggle}
            className="py-2 px-4 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center space-x-2"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isPlaying ? 'PAUSE REPLAY' : 'START REPLAY'}</span>
          </button>
          <button
            onClick={() => { setCurrentStep(0); setIsPlaying(false); }}
            className="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-orbitron"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Scrubber Progress Bar */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400">
          <span>Event {currentStep + 1} of {sampleTimelineEvents.length}</span>
          <span className="text-cyan-400 font-bold">{sampleTimelineEvents[currentStep]?.time}</span>
        </div>
        <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
          <div
            className="h-full bg-cyan-500 transition-all duration-300 glow-cyan"
            style={{ width: `${((currentStep + 1) / sampleTimelineEvents.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Timeline Event Flow Cards */}
      <div className="space-y-3 font-mono text-xs">
        {sampleTimelineEvents.map((evt, idx) => {
          const isActive = idx === currentStep;
          return (
            <div
              key={idx}
              className={`p-4 rounded-xl border transition-all ${
                isActive
                  ? 'bg-cyan-950/40 border-cyan-500/60 glow-cyan scale-[1.01]'
                  : 'bg-slate-900/60 border-slate-800 opacity-60'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-slate-400 font-orbitron">{evt.time}</span>
                  <span className="font-bold text-cyan-400">{evt.source}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                  <span className="font-bold text-indigo-400">{evt.dest}</span>
                </div>
                <span className="px-2 py-0.5 bg-slate-800 border border-slate-700 text-slate-300 rounded text-[10px]">
                  {evt.protocol}
                </span>
              </div>
              <p className="mt-2 text-slate-300">{evt.desc}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
