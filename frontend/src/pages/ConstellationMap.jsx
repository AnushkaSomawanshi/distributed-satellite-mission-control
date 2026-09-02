import React, { useState } from 'react';
import { Satellite, Radio, Zap, ShieldCheck, AlertCircle } from 'lucide-react';

export default function ConstellationMap({ satellites = [] }) {
  const [selectedSat, setSelectedSat] = useState(null);

  // Satellite node coordinates on orbital canvas
  const nodePositions = {
    'SAT-01': { x: 200, y: 150 },
    'SAT-02': { x: 500, y: 150 },
    'SAT-03': { x: 150, y: 350 },
    'SAT-04': { x: 550, y: 350 },
    'SAT-05': { x: 350, y: 480 }
  };

  const links = [
    { from: 'SAT-01', to: 'SAT-02', label: 'P2P Cross-link' },
    { from: 'SAT-01', to: 'SAT-03', label: 'P2P Cross-link' },
    { from: 'SAT-02', to: 'SAT-04', label: 'P2P Cross-link' },
    { from: 'SAT-03', to: 'SAT-05', label: 'P2P Link' },
    { from: 'SAT-04', to: 'SAT-05', label: 'P2P Link' }
  ];

  const getSatStatus = (satId) => {
    const s = satellites.find(x => x.satellite_id === satId);
    return s ? s.status : 'HEALTHY';
  };

  const getSatData = (satId) => {
    return satellites.find(x => x.satellite_id === satId) || {
      satellite_id: satId,
      status: 'HEALTHY',
      health_score: 100,
      battery: 98,
      temperature: 24,
      grpc_port: 5001,
      p2p_port: 6001
    };
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron">Constellation Topology & Network Graph</h2>
          <p className="text-xs text-slate-400 font-mono">Live LEO Satellite Nodes & Inter-Satellite P2P Links</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive SVG Canvas */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-800 relative min-h-[520px] flex items-center justify-center">
          <svg className="w-full h-full absolute inset-0" viewBox="0 0 700 550">
            {/* Orbital Ring Background */}
            <ellipse cx="350" cy="300" rx="280" ry="200" fill="none" stroke="#1e293b" strokeWidth="2" strokeDasharray="6 6" />

            {/* P2P Links */}
            {links.map((link, idx) => {
              const p1 = nodePositions[link.from];
              const p2 = nodePositions[link.to];
              const s1Status = getSatStatus(link.from);
              const s2Status = getSatStatus(link.to);
              const isOffline = s1Status === 'OFFLINE' || s2Status === 'OFFLINE';

              return (
                <g key={idx}>
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke={isOffline ? '#475569' : '#06b6d4'}
                    strokeWidth={isOffline ? '1.5' : '2'}
                    strokeDasharray={isOffline ? '4 4' : 'none'}
                    opacity={isOffline ? 0.4 : 0.7}
                  />
                  {!isOffline && (
                    <circle r="4" fill="#38bdf8">
                      <animateMotion
                        path={`M ${p1.x} ${p1.y} L ${p2.x} ${p2.y}`}
                        dur={`${2 + idx}s`}
                        repeatCount="indefinite"
                      />
                    </circle>
                  )}
                </g>
              );
            })}

            {/* Satellite Nodes */}
            {Object.keys(nodePositions).map((satId) => {
              const pos = nodePositions[satId];
              const data = getSatData(satId);
              const isOffline = data.status === 'OFFLINE';
              const isSelected = selectedSat?.satellite_id === satId;

              return (
                <g
                  key={satId}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  className="cursor-pointer group"
                  onClick={() => setSelectedSat(data)}
                >
                  <circle
                    r="24"
                    fill={isOffline ? '#1e293b' : '#0f172a'}
                    stroke={
                      isOffline ? '#64748b' :
                      data.status === 'WARNING' ? '#f59e0b' :
                      data.status === 'CRITICAL' ? '#ef4444' : '#06b6d4'
                    }
                    strokeWidth={isSelected ? '3.5' : '2'}
                    className={isSelected ? 'glow-cyan' : ''}
                  />
                  <text
                    y="5"
                    textAnchor="middle"
                    fill="#f8fafc"
                    fontSize="11"
                    fontWeight="bold"
                    fontFamily="Orbitron"
                  >
                    {satId.replace('SAT-', '')}
                  </text>
                  <text
                    y="40"
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize="10"
                    fontFamily="JetBrains Mono"
                  >
                    {satId}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Node Inspector Panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-slate-200 font-orbitron">Node Inspector</h3>
          {selectedSat ? (
            <div className="space-y-4 font-mono text-xs">
              <div className="p-4 bg-slate-900/80 border border-cyan-500/30 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-400 font-bold font-orbitron text-sm">{selectedSat.satellite_id}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    selectedSat.status === 'HEALTHY' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                  }`}>
                    {selectedSat.status}
                  </span>
                </div>
                <div className="text-slate-400 text-[11px]">Node ID: {selectedSat.node_id}</div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">gRPC Port:</span>
                  <span className="text-slate-200">{selectedSat.grpc_port}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">P2P Port:</span>
                  <span className="text-slate-200">{selectedSat.p2p_port}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Health Score:</span>
                  <span className="text-emerald-400 font-bold">{selectedSat.health_score}%</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Battery Level:</span>
                  <span className="text-slate-200">{selectedSat.battery}%</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Temperature:</span>
                  <span className="text-slate-200">{selectedSat.temperature}°C</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs">
              Click any satellite node on the topology map to inspect state.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
