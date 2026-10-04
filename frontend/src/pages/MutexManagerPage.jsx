import React, { useState } from 'react';
import { Lock, Unlock, Play, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';

export default function MutexManagerPage() {
  const [requester, setRequester] = useState('SAT-01');
  const [resourceId, setResourceId] = useState('T-047');
  const [mutexResult, setMutexResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRequest = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/mutex/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requester_id: requester, resource_id: resourceId })
      });
      const data = await res.json();
      setMutexResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRelease = async () => {
    try {
      const res = await fetch('/api/mutex/release', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requester_id: requester, resource_id: resourceId })
      });
      const data = await res.json();
      setMutexResult((prev) => ({ ...prev, status: 'RELEASED' }));
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center space-x-2">
            <Lock className="w-5 h-5 text-cyan-400" />
            <span>Ricart-Agrawala Distributed Mutual Exclusion</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Arbitrates concurrent task/resource ownership requests across satellite nodes using Lamport timestamps $T_i$ and peer replies.
          </p>
        </div>
      </div>

      {/* Control Form */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800/80 flex items-center justify-between flex-wrap gap-4 font-mono text-xs">
        <div className="flex items-center space-x-4">
          <div>
            <span className="text-slate-400">Requesting Node:</span>
            <select
              value={requester}
              onChange={(e) => setRequester(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2.5 py-1.5 ml-2 font-bold"
            >
              {['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div>
            <span className="text-slate-400">Resource / Task ID:</span>
            <input
              type="text"
              value={resourceId}
              onChange={(e) => setResourceId(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2.5 py-1.5 ml-2 font-bold w-28"
            />
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleRequest}
            disabled={loading}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl flex items-center space-x-2 transition-all glow-cyan"
          >
            <Lock className="w-4 h-4" />
            <span>Request Lock (Ricart-Agrawala)</span>
          </button>
          <button
            onClick={handleRelease}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-500/30 font-bold rounded-xl flex items-center space-x-2 transition-all"
          >
            <Unlock className="w-4 h-4" />
            <span>Release Lock</span>
          </button>
        </div>
      </div>

      {/* Execution Results */}
      {mutexResult && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 font-mono text-xs">
            <span className="font-bold text-slate-200">Protocol Execution Outcome</span>
            <span className={`px-2.5 py-1 rounded font-bold ${mutexResult.status === 'CRITICAL_SECTION_ENTERED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-300'}`}>
              {mutexResult.status}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono text-slate-300">
            <div><span className="text-slate-500">Requester:</span> {mutexResult.requester_id}</div>
            <div><span className="text-slate-500">Lamport T:</span> T={mutexResult.lamport_timestamp}</div>
            <div><span className="text-slate-500">Replies Granted:</span> {mutexResult.replies_granted?.length || 0}</div>
            <div><span className="text-slate-500">Latency:</span> {mutexResult.latency_ms} ms</div>
          </div>

          {/* Message Trace */}
          <div className="space-y-2 pt-2">
            <span className="font-mono text-xs text-slate-400">Peer Message Exchange Trace:</span>
            <div className="space-y-1 font-mono text-xs">
              {mutexResult.message_trace?.map((m, i) => (
                <div key={i} className="p-2 bg-slate-900/80 rounded border border-slate-800 flex items-center justify-between">
                  <span>{m.from_node} → {m.to_node} (T={m.timestamp_t_i})</span>
                  <span className={m.response === 'REPLY_GRANTED' ? 'text-emerald-400 font-bold' : 'text-amber-400'}>{m.response}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
