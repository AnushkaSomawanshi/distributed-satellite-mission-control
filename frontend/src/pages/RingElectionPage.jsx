import React, { useState } from 'react';
import { ShieldCheck, Play, ArrowRight, RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function RingElectionPage() {
  const [initiator, setInitiator] = useState('SAT-01');
  const [electionResult, setElectionResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runElection = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/election/ring?initiator_id=${initiator}`, { method: 'POST' });
      const data = await res.json();
      setElectionResult(data);
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
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
            <span>Genuine Message-Driven Ring Leader Election</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Satellite nodes circulate ELECTION & COORDINATOR messages directly around the ring topology. Offline nodes are bypassed.
          </p>
        </div>
      </div>

      {/* Control Panel */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800/80 flex items-center justify-between flex-wrap gap-4 font-mono text-xs">
        <div className="flex items-center space-x-3">
          <span className="text-slate-400">Select Initiating Node:</span>
          <select
            value={initiator}
            onChange={(e) => setInitiator(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-3 py-1.5 font-bold"
          >
            {['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <button
          onClick={runElection}
          disabled={loading}
          className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl flex items-center space-x-2 transition-all shadow-lg glow-cyan"
        >
          <Play className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Initiate Ring Election</span>
        </button>
      </div>

      {/* Ring Topology Graphic */}
      <div className="glass-panel p-6 rounded-xl border border-slate-800/80 space-y-4">
        <h3 className="font-orbitron font-semibold text-slate-200 text-sm">Ring Topology & Message Flow</h3>
        <div className="flex items-center justify-center space-x-4 font-mono text-xs overflow-x-auto py-4">
          {['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'].map((satId, idx) => {
            const isWinner = electionResult && electionResult.current_leader === satId;
            const isBypassed = electionResult && electionResult.failed_nodes?.includes(satId);
            return (
              <React.Fragment key={satId}>
                <div className={`p-4 rounded-xl border text-center font-bold transition-all ${
                  isWinner ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 glow-cyan scale-105' :
                  isBypassed ? 'bg-rose-500/10 border-rose-500/30 text-rose-400 line-through' :
                  'bg-slate-900 border-slate-800 text-slate-200'
                }`}>
                  <div>{satId}</div>
                  {isWinner && <div className="text-[10px] text-cyan-400 font-normal mt-1">LEADER</div>}
                  {isBypassed && <div className="text-[10px] text-rose-400 font-normal mt-1">BYPASSED</div>}
                </div>
                {idx < 4 && <ArrowRight className="w-5 h-5 text-slate-600 shrink-0" />}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Trace Log Table */}
      {electionResult && (
        <div className="glass-panel rounded-xl border border-slate-800/80 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between font-mono text-xs">
            <span className="font-bold text-slate-200">Election Message Execution Trace</span>
            <span className="text-cyan-400">Winner: {electionResult.current_leader} ({electionResult.latency_ms} ms)</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/50 text-slate-400 font-mono">
                  <th className="p-3">Step</th>
                  <th className="p-3">Message Type</th>
                  <th className="p-3">From</th>
                  <th className="p-3">To</th>
                  <th className="p-3">Highest Candidate</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {electionResult.election_trace?.map((t, i) => (
                  <tr key={i} className="hover:bg-slate-900/40">
                    <td className="p-3 text-slate-400">{t.step}</td>
                    <td className="p-3 text-cyan-300 font-bold">{t.message_type || 'ELECTION'}</td>
                    <td className="p-3 text-slate-200">{t.from_node || t.node}</td>
                    <td className="p-3 text-slate-200">{t.to_node || '-'}</td>
                    <td className="p-3 text-emerald-400 font-bold">{t.highest_candidate || t.new_leader || '-'}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${t.status === 'DELIVERED' || t.status === 'ANNOUNCED' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                        {t.status}
                      </span>
                    </td>
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
