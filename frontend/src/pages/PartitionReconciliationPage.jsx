import React, { useState } from 'react';
import { Network, Play, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';

export default function PartitionReconciliationPage() {
  const [partitionState, setPartitionState] = useState(null);
  const [reconcileResult, setReconcileResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const simulatePartition = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/partition/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_a: ['SAT-01', 'SAT-02'], group_b: ['SAT-03', 'SAT-04', 'SAT-05'] })
      });
      const data = await res.json();
      setPartitionState(data);
      setReconcileResult(null);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const reconcilePartition = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/partition/reconcile', { method: 'POST' });
      const data = await res.json();
      setReconcileResult(data);
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
            <Network className="w-5 h-5 text-cyan-400" />
            <span>Network Partition & Deterministic State Reconciliation</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Simulates constellation network split into Group A vs Group B, divergent vector clocks ($A \parallel B$), and vector merge state reconciliation upon partition healing.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={simulatePartition}
            disabled={loading}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded-xl text-xs flex items-center space-x-2 transition-all"
          >
            <AlertTriangle className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Simulate Network Partition</span>
          </button>
          <button
            onClick={reconcilePartition}
            disabled={loading || !partitionState}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs flex items-center space-x-2 transition-all glow-cyan"
          >
            <CheckCircle className="w-4 h-4" />
            <span>Heal & Reconcile State</span>
          </button>
        </div>
      </div>

      {/* Partition State Display */}
      {partitionState && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs">
          <div className="glass-panel p-5 rounded-xl border border-amber-500/40 bg-amber-500/5 space-y-3">
            <div className="font-bold text-amber-300 text-sm">Partition Group A</div>
            <div className="text-slate-300">Nodes: {partitionState.group_a?.join(', ')}</div>
            <div className="p-3 bg-slate-900 rounded border border-slate-800 text-cyan-300">
              Vector Clock: [{Object.values(partitionState.group_a_vector || {}).join(', ')}]
            </div>
          </div>

          <div className="glass-panel p-5 rounded-xl border border-amber-500/40 bg-amber-500/5 space-y-3">
            <div className="font-bold text-amber-300 text-sm">Partition Group B</div>
            <div className="text-slate-300">Nodes: {partitionState.group_b?.join(', ')}</div>
            <div className="p-3 bg-slate-900 rounded border border-slate-800 text-cyan-300">
              Vector Clock: [{Object.values(partitionState.group_b_vector || {}).join(', ')}]
            </div>
          </div>
        </div>
      )}

      {/* Reconciliation Outcome */}
      {reconcileResult && (
        <div className="glass-panel p-5 rounded-xl border border-emerald-500/40 bg-emerald-500/5 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between font-bold text-emerald-300 text-sm">
            <span>Partition Healed & State Reconciled</span>
            <span>Duration: {reconcileResult.duration_ms} ms</span>
          </div>
          <div className="text-slate-300">Strategy: {reconcileResult.conflict_resolution}</div>
          <div className="p-3 bg-slate-900 rounded border border-slate-800 text-emerald-400 font-bold">
            Merged Vector Clock: [{Object.values(reconcileResult.reconciled_vector_clock || {}).join(', ')}]
          </div>
        </div>
      )}
    </div>
  );
}
