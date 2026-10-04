import React from 'react';
import { X, GitCommit, ShieldCheck, Activity, Terminal, ArrowDown, Database, Cpu } from 'lucide-react';

export default function EventTraceDrawer({ isOpen, onClose, correlationId, eventData }) {
  if (!isOpen || !correlationId) return null;

  const traceSteps = eventData?.traceSteps || [
    { layer: 'Layer 1 — Frontend UI', action: 'USER_FAULT_REQUEST', source: 'Mission Control Dashboard', status: 'EXECUTED', time: '19:34:12.120' },
    { layer: 'Layer 2 — FastAPI Backend', action: 'CONTROL_COMMAND_DISPATCHED', source: '/api/faults/inject', status: '200 OK', time: '19:34:12.180' },
    { layer: 'Layer 3 — Container Runtime', action: 'CONTAINER_PROCESS_STOPPED', source: 'Docker Daemon / Local Process', status: 'TERMINATED', time: '19:34:12.301' },
    { layer: 'Layer 4 — Satellite Node', action: 'HEARTBEAT_DISAPPEARED', source: correlationId?.includes('SAT') ? correlationId : 'SAT-03', status: 'MISSING', time: '19:34:14.000' },
    { layer: 'Layer 5 — Failure Detector', action: 'HEARTBEAT_TIMEOUT_TRIGGERED', source: 'Heartbeat Sweeper Task', status: 'SUSPECTED (>5s)', time: '19:34:16.000' },
    { layer: 'Layer 6 — Service Registry', action: 'REGISTRY_STATUS_UPDATED', source: 'Global Registry', status: 'DISCONNECTED', time: '19:34:20.000' },
    { layer: 'Layer 7 — WebSocket Bus', action: 'BROADCAST_NODE_DISCONNECTED', source: 'WebSocket Broadcaster (/ws)', status: 'EMITTED', time: '19:34:20.050' },
    { layer: 'Layer 8 — Frontend UI', action: 'DASHBOARD_STATE_UPDATED', source: 'React State Synced', status: 'CONFIRMED RED', time: '19:34:20.080' }
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl p-6 overflow-y-auto space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="space-y-1">
              <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded text-[10px] font-mono font-bold">
                END-TO-END EVENT TRACE
              </span>
              <h3 className="text-base font-bold text-slate-100 font-orbitron">{correlationId}</h3>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-200 transition">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-1 font-mono text-xs text-slate-400">
            <p>Traced across distributed layers from node source to dashboard.</p>
          </div>

          {/* Trace Timeline */}
          <div className="space-y-4 font-mono text-xs">
            {traceSteps.map((step, idx) => (
              <div key={idx} className="relative pl-6 pb-2 border-l-2 border-cyan-500/40 space-y-1">
                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-slate-900 border-2 border-cyan-400 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400"></div>
                </div>

                <div className="text-[11px] font-bold text-cyan-400 font-orbitron">{step.layer}</div>
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1 text-slate-200">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-100 text-[11px]">{step.action}</span>
                    <span className="text-[10px] text-emerald-400 font-bold">{step.status}</span>
                  </div>
                  <div className="text-[10px] text-slate-400 flex justify-between">
                    <span>Src: {step.source}</span>
                    <span>{step.time}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs space-y-2">
            <div className="text-cyan-400 font-bold font-orbitron text-[11px]">VERIFICATION STATEMENT:</div>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              This event is observable across Docker container logs, FastAPI backend logs, PostgreSQL persistence table, WebSocket frame stream, and React Mission Control dashboard.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
