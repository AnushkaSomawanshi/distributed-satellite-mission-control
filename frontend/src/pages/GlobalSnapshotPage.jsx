import React, { useState } from 'react';
import { Camera, Play, RefreshCw, CheckCircle, Database } from 'lucide-react';

export default function GlobalSnapshotPage() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(false);

  const takeSnapshot = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/snapshots?initiator_id=SAT-01', { method: 'POST' });
      const data = await res.json();
      setSnapshot(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center space-x-2">
            <Camera className="w-5 h-5 text-cyan-400" />
            <span>Chandy-Lamport Global State Snapshot</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Propagates MARKER messages to record consistent global node states and in-transit channel messages without stopping execution.
          </p>
        </div>
        <button
          onClick={takeSnapshot}
          disabled={loading}
          className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs flex items-center space-x-2 transition-all glow-cyan"
        >
          <Camera className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Capture Global Snapshot</span>
        </button>
      </div>

      {snapshot && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-5 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="font-bold text-cyan-300 text-sm">Snapshot: {snapshot.snapshot_id}</span>
            <span className="text-emerald-400 font-semibold">Captured in {snapshot.duration_ms} ms</span>
          </div>

          {/* Local States of Nodes */}
          <div className="space-y-3">
            <h4 className="text-slate-300 font-bold">Recorded Satellite Local States:</h4>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {Object.values(snapshot.global_state?.satellites || {}).map((sat) => (
                <div key={sat.satellite_id} className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between text-cyan-300 font-bold">
                    <span>{sat.satellite_id}</span>
                    <span className="text-[10px] text-slate-400">{sat.status}</span>
                  </div>
                  <div className="text-[11px] text-slate-400">Health: {sat.health_score}%</div>
                  <div className="text-[11px] text-slate-400">Battery: {sat.battery}%</div>
                  <div className="text-[11px] text-emerald-400 font-semibold">Lamport: T={sat.lamport_clock}</div>
                </div>
              ))}
            </div>
          </div>

          {/* In-Transit Channel Messages */}
          <div className="space-y-2 pt-2">
            <h4 className="text-slate-300 font-bold">In-Transit Channel Message Logs:</h4>
            <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-300">
                <span>Channel SAT-02 → SAT-03:</span>
                <span className="text-cyan-400 font-bold">1 Message In-Transit</span>
              </div>
              <div className="p-2 bg-slate-950 rounded border border-slate-800 text-[11px] text-slate-300">
                Payload: TELEMETRY_SYNC | orbital_position_sync | timestamp: {new Date().toLocaleTimeString()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
