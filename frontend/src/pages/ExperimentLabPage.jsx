import React, { useState, useEffect } from 'react';
import { Cpu, Play, RefreshCw, BarChart2, ShieldCheck, CheckCircle } from 'lucide-react';

export default function ExperimentLabPage() {
  const [comparison, setComparison] = useState(null);
  const [experimentResult, setExperimentResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchComparison = async () => {
    try {
      const res = await fetch('/api/experiments/compare');
      const data = await res.json();
      setComparison(data);
    } catch (e) {
      console.error(e);
    }
  };

  const runExperiment = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/experiments/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: 'COORDINATOR_FAILURE', iterations: 3 })
      });
      const data = await res.json();
      setExperimentResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComparison();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center space-x-2">
            <BarChart2 className="w-5 h-5 text-cyan-400" />
            <span>Resilience Experiment Laboratory & Algorithm Comparison</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Controlled experiment framework evaluating message count, election duration, and recovery overhead across runs.
          </p>
        </div>
        <button
          onClick={runExperiment}
          disabled={loading}
          className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs flex items-center space-x-2 transition-all glow-cyan"
        >
          <Play className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Run 3-Iteration Resilience Experiment</span>
        </button>
      </div>

      {/* Algorithm Comparison Framework */}
      {comparison && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="font-bold text-cyan-300 text-sm">Election Strategy Benchmark Comparison</span>
            <span className="text-emerald-400 font-bold">Recommended: {comparison.recommended_algorithm}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {comparison.comparison?.map((alg, i) => (
              <div key={i} className="p-4 bg-slate-900 rounded-xl border border-slate-800 space-y-2">
                <div className="font-bold text-slate-200 text-sm">{alg.algorithm}</div>
                <div className="text-slate-400 space-y-1 text-[11px]">
                  <div>Messages Exchanged: <span className="text-cyan-300 font-bold">{alg.message_count}</span></div>
                  <div>Rounds: <span className="text-slate-200 font-bold">{alg.rounds}</span></div>
                  <div>Latency: <span className="text-emerald-400 font-bold">{alg.latency_ms} ms</span></div>
                  <div>Complexity: <span className="text-slate-300 font-bold">{alg.message_complexity}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Experiment Execution Results */}
      {experimentResult && (
        <div className="glass-panel p-5 rounded-xl border border-cyan-500/30 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="font-bold text-cyan-300 text-sm">Experiment Results: {experimentResult.experiment_id}</span>
            <span className="text-emerald-400 font-bold">Avg Resilience: {experimentResult.avg_resilience_score} / 100</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/50 text-slate-400">
                  <th className="p-3">Iteration Run</th>
                  <th className="p-3">Election Latency</th>
                  <th className="p-3">Messages Exchanged</th>
                  <th className="p-3">Tasks Reassigned</th>
                  <th className="p-3">Resilience Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {experimentResult.runs?.map((r) => (
                  <tr key={r.run} className="hover:bg-slate-900/40">
                    <td className="p-3 text-slate-300 font-bold">Run #{r.run}</td>
                    <td className="p-3 text-emerald-400">{r.election_latency_ms} ms</td>
                    <td className="p-3 text-cyan-300">{r.messages_exchanged}</td>
                    <td className="p-3 text-slate-200">{r.tasks_reassigned}</td>
                    <td className="p-3 text-cyan-400 font-bold">{r.resilience_score} / 100</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
