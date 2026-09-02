import React, { useState, useEffect } from 'react';
import { Satellite, Radio, ShieldCheck, AlertTriangle, Activity, Clock } from 'lucide-react';

export default function Header({ systemHealth, wsConnected }) {
  const [timeStr, setTimeStr] = useState(new Date().toUTCString());

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeStr(new Date().toUTCString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const totalSats = systemHealth?.satellites?.total || 5;
  const healthySats = systemHealth?.satellites?.healthy || 5;
  const isHealthy = (systemHealth?.status === 'HEALTHY');

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
      {/* Brand & Title */}
      <div className="flex items-center space-x-3.5">
        <div className="p-2.5 bg-cyan-500/10 border border-cyan-500/30 rounded-xl glow-cyan text-cyan-400">
          <Satellite className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-lg font-bold text-slate-100 tracking-wider font-orbitron">
              ORBITAL MISSION CONTROL
            </h1>
            <span className="px-2 py-0.5 text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded-md">
              FA-1 LAB
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Distributed Satellite Health Monitoring & Fault Recovery System
          </p>
        </div>
      </div>

      {/* Real-time Telemetry & Health Badges */}
      <div className="flex items-center space-x-6 text-xs font-mono">
        <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span className="text-slate-400">Nodes:</span>
          <span className="font-bold text-slate-200">{healthySats} / {totalSats} Active</span>
        </div>

        <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
          <Radio className={`w-4 h-4 ${wsConnected ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
          <span className="text-slate-400">WebSocket Stream:</span>
          <span className={`font-bold ${wsConnected ? 'text-emerald-400' : 'text-amber-400'}`}>
            {wsConnected ? 'LIVE (10 msg/s)' : 'CONNECTING...'}
          </span>
        </div>

        <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
          {isHealthy ? (
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          )}
          <span className="text-slate-400">System:</span>
          <span className={`font-bold ${isHealthy ? 'text-emerald-400' : 'text-amber-400'}`}>
            {systemHealth?.status || 'HEALTHY'}
          </span>
        </div>

        <div className="hidden lg:flex items-center space-x-2 text-slate-400 bg-slate-900/60 border border-slate-800/60 px-3 py-1.5 rounded-lg">
          <Clock className="w-4 h-4 text-slate-500" />
          <span>{timeStr}</span>
        </div>
      </div>
    </header>
  );
}
