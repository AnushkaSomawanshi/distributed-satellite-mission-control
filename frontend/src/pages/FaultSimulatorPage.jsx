import React, { useState, useEffect } from 'react';
import { Zap, AlertTriangle, RefreshCw, CheckCircle, ShieldAlert, Terminal, Split, RotateCcw, Activity } from 'lucide-react';
import FaultScenarioPanel from '../components/FaultScenarioPanel';

const defaultSatList = ['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'];

export default function FaultSimulatorPage({ satellites = [], activeFaults = [], onSelectCorrelationId }) {
  const [selectedSat, setSelectedSat] = useState('SAT-03');
  const [faultType, setFaultType] = useState('STOP_NODE');
  const [latencyVal, setLatencyVal] = useState(500);
  const [lossVal, setLossVal] = useState(20);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [satList, setSatList] = useState(defaultSatList);
  const [partitionState, setPartitionState] = useState(null);

  useEffect(() => {
    if (satellites && satellites.length > 0) {
      setSatList(satellites.map(s => s.satellite_id));
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

  const handleCreatePartition = async () => {
    try {
      const res = await fetch('/api/network/partition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          partition_a: ['SAT-01', 'SAT-02', 'SAT-03'],
          partition_b: ['SAT-04', 'SAT-05']
        })
      });
      const data = await res.json();
      setPartitionState(data.partitions);
      setResult({ status: 'PARTITIONED', data });
    } catch (e) {
      setResult({ status: 'ERROR', error: String(e) });
    }
  };

  const handleRestorePartition = async () => {
    try {
      const res = await fetch('/api/network/restore', { method: 'POST' });
      const data = await res.json();
      setPartitionState(null);
      setResult({ status: 'RECONCILED', data });
    } catch (e) {
      setResult({ status: 'ERROR', error: String(e) });
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron text-amber-400">
            Real Distributed Fault Simulator & Failure Detector
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Dual-source fault injection (Frontend UI vs Terminal Docker Stop), multistage failure lifecycle & network partition split
          </p>
        </div>
        <span className="px-3 py-1 bg-amber-500/20 text-amber-300 text-xs font-bold rounded-lg font-orbitron border border-amber-500/40">
          FAULT ENGINE ACTIVE
        </span>
      </div>

      {/* Dual Source Guidance Banner */}
      <div className="glass-panel p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
        <div className="space-y-1">
          <span className="font-bold text-amber-300 flex items-center space-x-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <span>METHOD A: FRONTEND FAULT CONTROL</span>
          </span>
          <p className="text-slate-300 text-[11px]">
            Inject node crash, latency, or temperature spikes directly using the buttons below. State updates propagate to satellite containers.
          </p>
        </div>

        <div className="space-y-1">
          <span className="font-bold text-cyan-300 flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>METHOD B: EXTERNAL DOCKER TERMINAL TEST</span>
          </span>
          <p className="text-slate-300 text-[11px]">
            Run <code className="bg-slate-900 px-1 py-0.5 rounded text-cyan-300 font-bold">docker stop satellite-03</code> in PowerShell. Heartbeat missing (&gt;5s SUSPECTED → &gt;10s DISCONNECTED) automatically updates frontend without clicking.
          </p>
        </div>
      </div>

      {/* Fault Scenario Explanation Panel */}
      <FaultScenarioPanel selectedFaultType={faultType} actualResult={result} />

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
                <option value="TEMP_SPIKE">Inject Temperature Spike (&gt;85°C Thermal Protection)</option>
                <option value="BATTERY_DRAIN">Inject Battery Drain (&lt;15% Power Saving)</option>
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

          {/* Network Partition Controls */}
          <div className="border-t border-slate-800 pt-4 space-y-3">
            <span className="text-xs font-bold text-cyan-400 font-orbitron flex items-center space-x-2">
              <Split className="w-4 h-4" />
              <span>Network Partition Simulation</span>
            </span>

            <div className="flex space-x-3">
              <button
                onClick={handleCreatePartition}
                className="flex-1 py-2.5 bg-rose-600/30 hover:bg-rose-600/50 border border-rose-500/40 text-rose-200 font-bold rounded-xl text-xs font-orbitron transition"
              >
                SPLIT PARTITIONS (A vs B)
              </button>
              <button
                onClick={handleRestorePartition}
                className="flex-1 py-2.5 bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/40 text-emerald-200 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-1"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>RECONCILE STATE</span>
              </button>
            </div>
          </div>

          {result && (
            <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-amber-400 font-bold font-orbitron">
                <span>EVENT RESPONSE:</span>
                <span className="text-emerald-400 font-bold">✓ EXECUTED 200 OK</span>
              </div>
              <pre className="text-[11px] text-amber-300 overflow-x-auto max-h-44 leading-relaxed">{JSON.stringify(result, null, 2)}</pre>
            </div>
          )}
        </div>

        {/* Active Faults & Node Health Status */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-base font-bold text-slate-200 font-orbitron">Failure Lifecycle & Latency Metrics</h3>

          <div className="space-y-3 font-mono text-xs">
            {satellites && satellites.length > 0 ? (
              satellites.map((s) => (
                <div key={s.satellite_id} className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
                  <div>
                    <div className="font-bold text-slate-200">{s.satellite_id}</div>
                    <div className="text-[10px] text-slate-400">
                      Src: {s.failure_source || 'SYSTEM'} | Det Latency: {s.detection_latency_ms || 0}ms
                    </div>
                  </div>
                  <span className={`px-2.5 py-1 rounded font-bold text-[10px] ${
                    s.status === 'HEALTHY' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                    s.status === 'SUSPECTED' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse' :
                    'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  }`}>
                    {s.status}
                  </span>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-slate-500 text-xs font-mono">
                Loading satellite health metrics...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
