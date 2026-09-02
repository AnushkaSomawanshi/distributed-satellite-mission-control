import React from 'react';
import { ArrowRight, CheckCircle2, AlertTriangle, Clock, Server, Terminal, Radio, ShieldCheck } from 'lucide-react';

export default function ExecutionTrace({
  title = "Distributed Execution Trace",
  protocol = "gRPC / HTTP",
  source = "Mission Control",
  destination = "SAT-03",
  status = "SUCCESS",
  latencyMs = 14.2,
  eventId = "EVT-EXEC-101",
  pathSteps = [],
  requestPayload = null,
  responsePayload = null,
  backendLog = null
}) {
  const isSuccess = status === "SUCCESS" || status === "HEALTHY" || status === "DELIVERED";

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 font-mono text-xs shadow-xl">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <div className={`p-1.5 rounded-lg ${isSuccess ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
            {isSuccess ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          </div>
          <div>
            <h4 className="font-bold text-slate-100 font-orbitron">{title}</h4>
            <span className="text-[10px] text-slate-400">Event ID: <strong className="text-cyan-400">{eventId}</strong></span>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-[11px]">
          <div className="px-2.5 py-1 bg-slate-900 rounded-lg border border-slate-800 flex items-center space-x-1.5">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-300">Latency: <strong className="text-cyan-400">{latencyMs} ms</strong></span>
          </div>
          <span className={`px-2.5 py-1 rounded-lg text-[10px] font-bold font-orbitron ${
            isSuccess ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
          }`}>
            {status}
          </span>
        </div>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px] text-slate-300">
        <div className="p-2.5 bg-slate-900/90 rounded-xl border border-slate-800 space-y-0.5">
          <span className="text-slate-400 text-[10px]">Protocol:</span>
          <div className="font-bold text-cyan-300 font-orbitron truncate">{protocol}</div>
        </div>
        <div className="p-2.5 bg-slate-900/90 rounded-xl border border-slate-800 space-y-0.5">
          <span className="text-slate-400 text-[10px]">Source Node:</span>
          <div className="font-bold text-slate-200 font-orbitron truncate">{source}</div>
        </div>
        <div className="p-2.5 bg-slate-900/90 rounded-xl border border-slate-800 space-y-0.5">
          <span className="text-slate-400 text-[10px]">Target Destination:</span>
          <div className="font-bold text-indigo-300 font-orbitron truncate">{destination}</div>
        </div>
        <div className="p-2.5 bg-slate-900/90 rounded-xl border border-slate-800 space-y-0.5">
          <span className="text-slate-400 text-[10px]">Verification Status:</span>
          <div className="font-bold text-emerald-400 font-orbitron truncate">REAL BACKEND EXECUTION</div>
        </div>
      </div>

      {/* Visual Execution Path Diagram */}
      {pathSteps && pathSteps.length > 0 && (
        <div className="p-3.5 bg-slate-950/90 rounded-xl border border-slate-800 space-y-2">
          <span className="text-slate-400 text-[10px] font-bold uppercase tracking-wider font-orbitron">Execution Path Sequence:</span>
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            {pathSteps.map((step, idx) => (
              <React.Fragment key={idx}>
                <span className="px-2.5 py-1 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 font-orbitron">
                  {step}
                </span>
                {idx < pathSteps.length - 1 && (
                  <ArrowRight className="w-3.5 h-3.5 text-cyan-400 shrink-0 animate-pulse" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Request & Response Payloads */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
        {requestPayload && (
          <div className="space-y-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase font-orbitron">Request Payload:</span>
            <pre className="text-[11px] text-cyan-300 p-3 bg-slate-950/95 rounded-xl border border-slate-800 overflow-x-auto max-h-44 leading-relaxed font-mono">
              {typeof requestPayload === 'string' ? requestPayload : JSON.stringify(requestPayload, null, 2)}
            </pre>
          </div>
        )}

        {responsePayload && (
          <div className="space-y-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase font-orbitron">Response Payload Evidence:</span>
            <pre className="text-[11px] text-emerald-300 p-3 bg-slate-950/95 rounded-xl border border-slate-800 overflow-x-auto max-h-44 leading-relaxed font-mono">
              {typeof responsePayload === 'string' ? responsePayload : JSON.stringify(responsePayload, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {backendLog && (
        <div className="p-3 bg-slate-950/90 rounded-xl border border-slate-800 text-[11px] font-mono text-slate-400 flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>Backend Log Evidence: <code className="text-slate-200">{backendLog}</code></span>
        </div>
      )}
    </div>
  );
}
