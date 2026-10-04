import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldAlert, Cpu, Activity, RefreshCw, Zap, ArrowRight } from 'lucide-react';

export default function FailureIntelligencePage() {
  const [selectedNode, setSelectedNode] = useState('SAT-03');
  const [classification, setClassification] = useState(null);
  const [predictiveData, setPredictiveData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchFailureData = async () => {
    setLoading(true);
    try {
      const res1 = await fetch(`/api/failure/classify/${selectedNode}`);
      const data1 = await res1.json();
      setClassification(data1);

      const res2 = await fetch('/api/predictive/evaluate');
      const data2 = await res2.json();
      setPredictiveData(data2);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFailureData();
  }, [selectedNode]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-orbitron text-slate-100 flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-cyan-400" />
            <span>Autonomous Failure Intelligence & Predictive Health Engine</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Multi-class failure classifier (12 categories) and proactive preemption warning subsystem.
          </p>
        </div>
        <button
          onClick={fetchFailureData}
          disabled={loading}
          className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-cyan-500/40 text-slate-200 rounded-xl text-xs font-semibold flex items-center space-x-2 transition-all"
        >
          <RefreshCw className={`w-4 h-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Intelligence</span>
        </button>
      </div>

      {/* Select Satellite */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 flex items-center space-x-4 font-mono text-xs">
        <span className="text-slate-400">Select Satellite Node to Inspect:</span>
        <div className="flex space-x-2">
          {['SAT-01', 'SAT-02', 'SAT-03', 'SAT-04', 'SAT-05'].map((s) => (
            <button
              key={s}
              onClick={() => setSelectedNode(s)}
              className={`px-3 py-1.5 rounded-lg border font-bold transition-all ${
                selectedNode === s
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 glow-cyan'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Failure Classification Result */}
      {classification && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="font-bold text-cyan-300 text-sm">Classification Result: {classification.node_id}</span>
            <span className="px-2.5 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded font-bold uppercase">
              Class: {classification.failure_class}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-slate-300">
            <div><span className="text-slate-500">Status:</span> {classification.status}</div>
            <div><span className="text-slate-500">Is Coordinator:</span> {classification.is_coordinator ? 'YES' : 'NO'}</div>
            <div><span className="text-slate-500">Confidence:</span> {(classification.confidence * 100).toFixed(0)}%</div>
          </div>

          <div className="p-3 bg-slate-900 rounded border border-slate-800 space-y-1">
            <span className="text-slate-400 font-semibold">Probable Root Cause:</span>
            <p className="text-slate-200 font-bold">{classification.probable_cause}</p>
          </div>
        </div>
      )}

      {/* Predictive Preemption Warnings */}
      {predictiveData && (
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="font-bold text-slate-200 text-sm">Constellation Predictive Risk Warnings</span>
            <span className="text-cyan-400 font-bold">{predictiveData.warnings_count} Warning Alerts</span>
          </div>

          {predictiveData.node_warnings?.length > 0 ? (
            <div className="space-y-3">
              {predictiveData.node_warnings.map((w, i) => (
                <div key={i} className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-2">
                  <div className="flex items-center justify-between font-bold text-amber-300">
                    <span>{w.satellite_id} — Preemptive Health Risk</span>
                    <span className="text-[10px] px-2 py-0.5 bg-amber-500/20 rounded">{w.risk_level}</span>
                  </div>
                  <div className="text-slate-300">Risk Factors: {w.risk_factors.join(', ')}</div>
                  <div className="text-emerald-300 font-semibold">{w.recommendation}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-slate-900/60 rounded text-slate-400 text-center">
              All 5 satellite nodes are operating within nominal health metrics. No preemptive task migration required.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
