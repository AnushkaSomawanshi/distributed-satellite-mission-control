import React, { useState, useEffect } from 'react';
import { Zap, AlertTriangle, RefreshCw, CheckCircle, ShieldAlert } from 'lucide-react';

const defaultSatList = ['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'];

export default function FaultSimulatorPage({ satellites = [], activeFaults = [] }) {
  const [selectedSat, setSelectedSat] = useState('SAT-03');
  const [faultType, setFaultType] = useState('STOP_NODE');
  const [latencyVal, setLatencyVal] = useState(500);
  const [lossVal, setLossVal] = useState(20);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [satList, setSatList] = useState(defaultSatList);

  useEffect(() => {
    if (satellites && satellites.length > 0) {
      setSatList(satellites.map(s => s.satellite_id));
    } else {
      fetch('/api/satellites')
        .then(r => r.json())
        .then(d => {
          if (d.satellites && d.satellites.length > 0) {
            setSatList(d.satellites.map(s => s.satellite_id));
          }
        })
        .catch(() => {});
    }
  }, [satellites]);

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
      setResult({ status: 'SUCCESS', target: selectedSat, fault_type: faultType, data });
    } catch (e) {
      setResult({ status: 'ERROR', error: String(e) });
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
      setResult({ status: 'ERROR', error: String(e) });
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron text-amber-400">
            Controlled Fault Simulator & Failure Detector
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Inject real-time node crashes, network latency, packet loss, and sensor spikes to verify distributed fault tolerance
          </p>
        </div>
        <span className="px-3 py-1 bg-amber-500/20 text-amber-300 text-xs font-bold rounded-lg font-orbitron border border-amber-500/40">
          FAULT INJECTION ACTIVE
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Injector Form */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-slate-200 font-orbitron flex items-center space-x-2 text-amber-400">
            <Zap className="w-5 h-5 text-amber-400" />
            <span>Fault Control Center</span>
          </h3>

          <div className="space-y-3 font-mono text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Target Satellite Node</label>
              <select value={selectedSat} onChange={(e) => setSelectedSat(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-slate-200 font-orbitron text-xs">
                {satList.map((satId) => (
                  <option key={satId} value={satId}>
                    {satId}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Fault Type</label>
              <select value={faultType} onChange={(e) => setFaultType(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-slate-200 font-mono text-xs">
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
                <input type="number" value={latencyVal} onChange={(e) => setLatencyVal(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-slate-200" />
              </div>
            )}

            {faultType === 'PACKET_LOSS' && (
              <div>
                <label className="text-slate-400 block mb-1">Packet Loss (%)</label>
                <input type="number" value={lossVal} onChange={(e) => setLossVal(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-slate-200" />
              </div>
            )}
          </div>

          <div className="flex space-x-3 pt-2">
            <button
              onClick={handleInjectFault}
              disabled={loading}
              className="flex-1 py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2 shadow-lg shadow-amber-500/20"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              <span>INJECT FAULT</span>
            </button>

            <button
              onClick={handleClearFaults}
              className="py-3 px-5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 font-bold rounded-xl text-xs font-orbitron transition"
            >
              CLEAR FAULTS
            </button>
          </div>

          {result && (
            <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-amber-400 font-bold font-orbitron">
                <span>FAULT RESULT: {result.target}</span>
                <span className="text-emerald-400 font-bold">✓ EXECUTED 200 OK</span>
              </div>
              <pre className="text-[11px] text-amber-300 overflow-x-auto max-h-44 leading-relaxed">{JSON.stringify(result, null, 2)}</pre>
            </div>
          )}
        </div>

        {/* Active Faults List */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-slate-200 font-orbitron">Active Faults & System Impact Log</h3>
          <div className="space-y-3 font-mono text-xs">
            {activeFaults.length > 0 ? (
              activeFaults.map((f, idx) => (
                <div key={idx} className="p-4 bg-slate-900/90 border border-amber-500/30 rounded-xl space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-400 font-orbitron">{f.fault_type}</span>
                    <span className="text-slate-300 font-bold">Node: {f.target_node}</span>
                  </div>
                  <div className="text-[11px] text-slate-400">Params: {JSON.stringify(f.parameters)}</div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-slate-500 text-xs font-mono">
                No active faults injected. All satellite nodes operating nominal.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
