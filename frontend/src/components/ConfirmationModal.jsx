import React from 'react';
import { AlertTriangle, ShieldAlert, X } from 'lucide-react';

export default function ConfirmationModal({ isOpen, onClose, onConfirm, title, message, targetNode, actionType }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="glass-panel max-w-md w-full p-6 rounded-2xl border border-amber-500/40 shadow-2xl space-y-5 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 text-amber-400 font-orbitron font-bold">
          <ShieldAlert className="w-6 h-6 text-amber-400 animate-pulse" />
          <h3 className="text-base">{title || 'CONFIRM DESTRUCTIVE ACTION'}</h3>
        </div>

        <div className="space-y-3 font-mono text-xs text-slate-300">
          <p className="leading-relaxed">
            {message || `Are you sure you want to execute ${actionType} on satellite node ${targetNode}?`}
          </p>

          <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1.5 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-400">Target Node:</span>
              <span className="text-cyan-400 font-bold font-orbitron">{targetNode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Action:</span>
              <span className="text-amber-400 font-bold font-orbitron">{actionType}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Impact:</span>
              <span className="text-rose-400 font-bold">Heartbeat Loss & State Change</span>
            </div>
          </div>
        </div>

        <div className="flex space-x-3 pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 font-bold rounded-xl text-xs font-orbitron transition"
          >
            CANCEL
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className="flex-1 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition shadow-lg shadow-amber-500/20"
          >
            CONFIRM & EXECUTE
          </button>
        </div>
      </div>
    </div>
  );
}
