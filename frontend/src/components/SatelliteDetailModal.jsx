import React, { useState } from 'react';
import { X, Satellite, Activity, Zap, Radio, Wifi, Video, ShieldCheck, AlertTriangle, Layers, Cpu, Server } from 'lucide-react';

export default function SatelliteDetailModal({ isOpen, onClose, satellite }) {
  const [activeTab, setActiveTab] = useState('overview'); // overview, source, health, protocols

  if (!isOpen || !satellite) return null;

  const getHealthBreakdown = (sat) => {
    const bat = Number(sat.battery || 100);
    const temp = Number(sat.temperature || 25);
    const cpu = Number(sat.cpu_usage || 15);
    const mem = Number(sat.memory_usage || 30);
    const sig = Number(sat.signal_strength || 95);

    const bScore = Math.min(25, 25 * (bat / 70));
    const tScore = (temp >= 15 && temp <= 45) ? 25 : (temp <= 75 ? 10 : 0);
    const cScore = cpu <= 70 ? 20 : 5;
    const mScore = mem <= 80 ? 15 : 5;
    const sScore = Math.min(15, 15 * (sig / 60));

    return {
      batteryScore: bScore.toFixed(1),
      tempScore: tScore.toFixed(1),
      cpuScore: cScore.toFixed(1),
      memScore: mScore.toFixed(1),
      sigScore: sScore.toFixed(1),
      totalScore: (bScore + tScore + cScore + mScore + sScore).toFixed(1)
    };
  };

  const breakdown = getHealthBreakdown(satellite);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="glass-panel max-w-2xl w-full p-6 rounded-2xl border border-slate-800 shadow-2xl space-y-5 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition">
          <X className="w-5 h-5" />
        </button>

        {/* Header Info */}
        <div className="flex items-center space-x-4 border-b border-slate-800 pb-4">
          <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl text-cyan-400">
            <Satellite className="w-8 h-8" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xl font-bold text-slate-100 font-orbitron text-cyan-400">{satellite.satellite_id}</h3>
              <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                satellite.status === 'HEALTHY' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                satellite.status === 'SUSPECTED' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              }`}>
                {satellite.status}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Node ID: {satellite.node_id || `NODE-${satellite.satellite_id}`} | gRPC: {satellite.grpc_port} | P2P: {satellite.p2p_port}
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 text-xs font-orbitron font-bold">
          {[
            { id: 'overview', label: 'OVERVIEW & METRICS' },
            { id: 'source', label: 'TELEMETRY SOURCE' },
            { id: 'health', label: 'HEALTH ANALYSIS' },
            { id: 'protocols', label: 'PROTOCOLS' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-4 border-b-2 transition ${
                activeTab === tab.id
                  ? 'border-cyan-400 text-cyan-400 bg-cyan-500/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab 1: Overview & Metrics */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-2 gap-3 font-mono text-xs">
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-400 block mb-1">Health Score</span>
              <span className="text-emerald-400 font-bold text-lg font-orbitron">{satellite.health_score || 100}%</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-400 block mb-1">Battery Level</span>
              <span className="text-cyan-400 font-bold text-lg font-orbitron">{satellite.battery || 95}%</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-400 block mb-1">Temperature</span>
              <span className="text-slate-200 font-bold text-lg font-orbitron">{satellite.temperature || 24}°C</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-400 block mb-1">CPU / Memory</span>
              <span className="text-slate-200 font-bold text-lg font-orbitron">{satellite.cpu_usage || 15}% / {satellite.memory_usage || 30}%</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-400 block mb-1">Last Heartbeat</span>
              <span className="text-slate-200 font-bold">{satellite.seconds_since_heartbeat !== undefined ? `${satellite.seconds_since_heartbeat}s ago` : 'Active'}</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-400 block mb-1">Power Mode</span>
              <span className="text-amber-400 font-bold font-orbitron">{satellite.power_mode || 'NORMAL'}</span>
            </div>
          </div>
        )}

        {/* Tab 2: Telemetry Source Evidence */}
        {activeTab === 'source' && (
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs space-y-3">
            <div className="text-cyan-400 font-bold font-orbitron text-sm flex items-center space-x-2">
              <Activity className="w-4 h-4" />
              <span>DYNAMIC TELEMETRY GENERATOR SOURCE</span>
            </div>

            <div className="space-y-2 text-slate-300">
              <p className="leading-relaxed">
                Telemetry values for <strong className="text-cyan-400">{satellite.satellite_id}</strong> are generated independently inside its containerized Python microservice (<code className="text-amber-300 font-bold">satellites/satellite_node.py</code>).
              </p>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg space-y-1.5 text-[11px]">
                <div><span className="text-slate-400">Generation Module:</span> <code className="text-slate-200">SatelliteNode.step_telemetry()</code></div>
                <div><span className="text-slate-400">Update Frequency:</span> <code className="text-slate-200">{satellite.power_mode === 'POWER_SAVING' ? '5.0 sec (Power Saving)' : '2.0 sec'}</code></div>
                <div><span className="text-slate-400">Transport Layer:</span> <code className="text-slate-200">RabbitMQ AMQP + WebSocket /ws</code></div>
                <div><span className="text-slate-400">Runtime Container:</span> <code className="text-slate-200">sat-0{satellite.satellite_id?.split('-')[1] || '1'}</code></div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Health Factor Analysis */}
        {activeTab === 'health' && (
          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
              <div className="flex justify-between items-center text-cyan-400 font-bold font-orbitron">
                <span>HEALTH CALCULATION SCORE: {breakdown.totalScore} / 100</span>
                <span>STATUS: {satellite.status}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 bg-slate-900 rounded">Battery Score: <strong className="text-cyan-300">{breakdown.batteryScore} / 25</strong></div>
                <div className="p-2 bg-slate-900 rounded">Temp Score: <strong className="text-cyan-300">{breakdown.tempScore} / 25</strong></div>
                <div className="p-2 bg-slate-900 rounded">CPU Score: <strong className="text-cyan-300">{breakdown.cpuScore} / 20</strong></div>
                <div className="p-2 bg-slate-900 rounded">Memory Score: <strong className="text-cyan-300">{breakdown.memScore} / 15</strong></div>
              </div>
            </div>

            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1 text-[11px]">
              <span className="text-slate-400 block font-bold">HEALTH SCORE RULE THRESHOLDS:</span>
              <div className="text-emerald-400">90 – 100 → HEALTHY</div>
              <div className="text-amber-400">70 – 89 → WARNING</div>
              <div className="text-orange-400">40 – 69 → DEGRADED</div>
              <div className="text-rose-400">0 – 39 → CRITICAL</div>
            </div>
          </div>
        )}

        {/* Tab 4: Protocol Status */}
        {activeTab === 'protocols' && (
          <div className="space-y-2 font-mono text-xs">
            {[
              { name: 'gRPC Interface', port: satellite.grpc_port, protocol: 'HTTP/2 Protobuf', status: satellite.status === 'HEALTHY' ? '● CONNECTED' : '🔴 UNAVAILABLE' },
              { name: 'RabbitMQ AMQP', port: 5672, protocol: 'AMQP Fanout Exchange', status: '● PUBLISHING' },
              { name: 'WebSocket Telemetry', port: 8000, protocol: 'JSON Stream /ws', status: '● STREAMING' },
              { name: 'Direct P2P Link', port: satellite.p2p_port, protocol: 'HTTP/1.1 TCP Socket', status: satellite.status === 'HEALTHY' ? '● LISTENING' : '🔴 UNAVAILABLE' },
              { name: 'WebRTC Camera', port: 'Signaling', protocol: 'SRTP / VP8 Stream', status: satellite.status === 'HEALTHY' ? '● LIVE' : '🔴 STREAM LOST' }
            ].map((p, idx) => (
              <div key={idx} className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-200">{p.name}</div>
                  <div className="text-[10px] text-slate-400">Port: {p.port} | Protocol: {p.protocol}</div>
                </div>
                <span className={`font-bold ${p.status.includes('●') ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {p.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
