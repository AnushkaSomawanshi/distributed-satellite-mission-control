import React, { useState } from 'react';
import { Zap, AlertTriangle, RefreshCw, CheckCircle, ShieldAlert } from 'lucide-react';

export default function FaultSimulatorPage({ satellites = [], activeFaults = [] }) {
  const [selectedSat, setSelectedSat] = useState('SAT-03');
  const [faultType, setFaultType] = useState('STOP_NODE');
  const [latencyVal, setLatencyVal] = useState(500);
  const [lossVal, setLossVal] = useState(20);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInjectFault = async () => {
    setLoading(true);
    let params = {};
    if (faultType === 'HIGH_LATENCY') params = { latency_ms: Number(latencyVal) };
    if (faultType === 'PACKET_LOSS') params = { loss_pct: Number(lossVal) };

    try {
      const res = await fetch('/api/faults/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fault_type: faultType,
          target_node: selectedSat,
          parameters: params
        })
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ status: 'ERROR', error: str(e) });
    } finally {
      setLoading(false);
    }
  };

  const handleClearFaults = async () => {
    try {
      const res = await fetch(`/api/faults/clear?target_node=${selectedSat}`, { method: 'POST' });
      const data = await res.json();
      setResult({ status: 'CLEARED', data });
    } catch (e) {
      setResult({ status: 'ERROR', error: str(e) });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100 font-orbitron">Controlled Fault Simulator</h2>
        <p className="text-xs text-slate-400 font-mono">
          Inject real-time node crashes, network latency, packet loss, and sensor spikes to verify distributed fault tolerance
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Injector Form */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-slate-200 font-orbitron flex items-center space-x-2 text-amber-400">
            <Zap className="w-5 h-5" />
            <span>Fault Control Center</span>
          </h3>

          <div className="space-y-3 font-mono text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Target Satellite Node</label>
              <select value={selectedSat} onChange={(e) => setSelectedSat(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-200">
                {satellites.map((s) => (
                  <option key={s.satellite_id} value={s.satellite_id}>
                    {s.satellite_id} ({s.status})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Fault Type</label>
              <select value={faultType} onChange={(e) => setFaultType(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-200">
                <option value="STOP_NODE">Stop Satellite Node (Simulate Crash / Offline)</option>
                <option value="RESTART_NODE">Restart Satellite Node (Simulate Recovery)</option>
                <option value="HIGH_LATENCY">Inject High Network Latency</option>
                <option value="PACKET_LOSS">Inject Packet / Message Loss</option>
                <option value="TEMP_SPIKE">Inject Solar Flare Temperature Spike (&gt;85°C)</option>
                <option value="BATTERY_DRAIN">Inject Eclipse Battery Drain (&lt;15%)</option>
                <option value="CPU_OVERLOAD">Inject CPU Overload (98%)</option>
              </select>
            </div>

            {faultType === 'HIGH_LATENCY' && (
              <div>
                <label className="text-slate-400 block mb-1">Latency (ms)</label>
                <input type="number" value={latencyVal} onChange={(e) => setLatencyVal(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-200" />
              </div>
            )}

            {faultType === 'PACKET_LOSS' && (
              <div>
                <label className="text-slate-400 block mb-1">Packet Loss (%)</label>
                <input type="number" value={lossVal} onChange={(e) => setLossVal(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-slate-200" />
              </div>
            )}
          </div>

          <div className="flex space-x-3 pt-2">
            <button
              onClick={handleInjectFault}
              disabled={loading}
              className="flex-1 py-3 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              <span>INJECT FAULT</span>
            </button>

            <button
              onClick={handleClearFaults}
              className="py-3 px-5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-bold rounded-xl text-xs font-orbitron transition"
            >
              CLEAR FAULTS
            </button>
          </div>

          {result && (
            <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2 font-mono text-xs">
              <div className="text-amber-400 font-bold font-orbitron">Fault Action Log</div>
              <pre className="text-[11px] text-slate-300 overflow-x-auto max-h-36">{JSON.stringify(result, null, 2)}</pre>
            </div>
          )}
        </div>

        {/* Active Faults List */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-slate-200 font-orbitron">Active Faults Log</h3>
          <div className="space-y-3 font-mono text-xs">
            {activeFaults.length > 0 ? (
              activeFaults.map((f, idx) => (
                <div key={idx} className="p-4 bg-slate-900/80 border border-amber-500/30 rounded-xl space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-400">{f.fault_type}</span>
                    <span className="text-slate-400">Node: {f.target_node}</span>
                  </div>
                  <div className="text-[11px] text-slate-400">Params: {JSON.stringify(f.parameters)}</div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-slate-500 text-xs">
                No active faults injected. All satellite nodes running nominal.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
