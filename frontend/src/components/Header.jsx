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

  const totalSats = systemHealth?.satellites?.total;
  const healthySats = systemHealth?.satellites?.healthy;
  const isHealthy = (systemHealth?.status === 'HEALTHY');

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 px-4 py-2 flex flex-nowrap items-center justify-between gap-3">
      {/* Brand & Title */}
      <div className="flex items-center space-x-3 shrink-0">
        <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg glow-cyan text-cyan-400">
          <Satellite className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base font-bold text-slate-100 tracking-wider font-orbitron">
              ORBITTRACK
            </h1>
            <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded-md">
              LIVE OPERATIONS
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono">
            Satellite Fleet Operations
          </p>
        </div>
      </div>

      {/* Real-time Telemetry & Health Badges */}
      <div className="flex min-w-0 items-center space-x-2 text-[10px] font-mono">
        <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-2 py-1 rounded-lg">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span className="text-slate-400">Satellites:</span>
          <span className="font-bold text-slate-200">{healthySats ?? '—'} / {totalSats ?? '—'} Active</span>
        </div>

        <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
          <Radio className={`w-4 h-4 ${wsConnected ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
          <span className="text-slate-400">Live event stream:</span>
          <span className={`font-bold ${wsConnected ? 'text-emerald-400' : 'text-amber-400'}`}>
            {wsConnected ? 'CONNECTED' : 'CONNECTING...'}
          </span>
        </div>

        <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span className="text-slate-400">Coordinator:</span>
          <span className="font-bold text-cyan-300 font-orbitron">{systemHealth?.current_leader || 'Unassigned'}</span>
        </div>

        <div className="flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg">
          {isHealthy ? (
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          )}
          <span className="text-slate-400">System:</span>
          <span className={`font-bold ${isHealthy ? 'text-emerald-400' : 'text-amber-400'}`}>
            {systemHealth?.status || 'UNKNOWN'}
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
