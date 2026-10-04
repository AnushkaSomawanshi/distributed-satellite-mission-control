import React, { useState, useEffect } from 'react';
import { Clock, RefreshCw, Zap, ShieldCheck, Activity, CheckCircle, ArrowRight } from 'lucide-react';

export default function ClockSyncPage() {
  const [clockStatus, setClockStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState(null);

  const fetchClockStatus = async () => {
    try {
      const res = await fetch('/api/clocks/status');
      const data = await res.json();
      setClockStatus(data);
    } catch (e) {
      console.error(e);
    }
  };

  const runSyncRound = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/clocks/synchronize', { method: 'POST' });
      const data = await res.json();
      setLastSyncResult(data);
      fetchClockStatus();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClockStatus();
  }, []);

  const pClocks = clockStatus?.physical_clocks || {};
  const lClocks = clockStatus?.lamport_clocks || {};
  const vClocks = clockStatus?.vector_clocks || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center space-x-2">
            <Clock className="w-5 h-5 text-cyan-400" />
            <span>Distributed Time & Synchronization Subsystem</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Physical Clock Synchronization (Christian's Algorithm), Lamport Logical Ordering, and Vector Clock Causality ($A \parallel B$).
          </p>
        </div>
        <button
          onClick={runSyncRound}
          disabled={loading}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs flex items-center space-x-2 transition-all shadow-lg glow-cyan"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Run Clock Synchronization Round</span>
        </button>
      </div>

      {/* Sync Round Result Banner */}
      {lastSyncResult && (
        <div className="glass-panel p-4 rounded-xl border border-emerald-500/40 bg-emerald-500/5 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-emerald-300 font-bold">
            <span>PHYSICAL CLOCK SYNCHRONIZATION ROUND COMPLETED</span>
            <span>Avg Offset: {lastSyncResult.avg_offset_ms} ms</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono text-slate-300">
            <div><span className="text-slate-500">Nodes Synced:</span> {lastSyncResult.node_count}</div>
            <div><span className="text-slate-500">Max Offset:</span> {lastSyncResult.max_offset_ms} ms</div>
            <div><span className="text-slate-500">Min Offset:</span> {lastSyncResult.min_offset_ms} ms</div>
            <div><span className="text-slate-500">Status:</span> {lastSyncResult.status}</div>
          </div>
        </div>
      )}

      {/* Physical Clocks Matrix */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4">
        <h3 className="font-orbitron font-semibold text-slate-200 text-sm flex items-center space-x-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span>Physical Clock Drift & Christian's Offset Metrics</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 font-mono text-xs">
          {['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'].map((satId) => {
            const info = pClocks[satId] || {};
            const offset = info.calculated_offset_ms ?? info.offset_ms ?? 0.0;
            const rtt = info.rtt_ms ?? 24.0;
            const err = info.residual_error_ms ?? (rtt / 2.0);
            return (
              <div key={satId} className="bg-slate-900/80 p-3.5 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between font-bold text-cyan-300">
                  <span>{satId}</span>
                  <span className="text-[10px] text-emerald-400">SYNCED</span>
                </div>
                <div className="text-slate-400 text-[11px] space-y-1">
                  <div>Offset: <span className="text-slate-200 font-bold">{offset} ms</span></div>
                  <div>RTT Delay: <span className="text-slate-200">{rtt} ms</span></div>
                  <div>Residual Error: <span className="text-slate-200">±{err} ms</span></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Logical & Vector Clocks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4">
          <h3 className="font-orbitron font-semibold text-slate-200 text-sm">Lamport Logical Clocks</h3>
          <div className="divide-y divide-slate-800">
            {Object.entries(lClocks).map(([satId, val]) => (
              <div key={satId} className="py-2.5 flex items-center justify-between font-mono text-xs">
                <span className="text-slate-300 font-bold">{satId}</span>
                <span className="text-cyan-400 font-bold">L = {val}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4">
          <h3 className="font-orbitron font-semibold text-slate-200 text-sm">Vector Clocks [SAT-01..SAT-05]</h3>
          <div className="divide-y divide-slate-800 font-mono text-xs">
            {Object.entries(vClocks).map(([satId, vec]) => (
              <div key={satId} className="py-2.5 flex items-center justify-between">
                <span className="text-slate-300 font-bold">{satId}</span>
                <span className="text-emerald-400 font-semibold bg-slate-900 px-2 py-1 rounded border border-slate-800">
                  [{Object.values(vec).join(', ')}]
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
