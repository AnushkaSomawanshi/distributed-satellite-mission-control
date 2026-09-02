import React, { useState } from 'react';
import { Send, Zap, Radio, Terminal, Cpu, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';

export default function CommunicationObservatory({ observatoryStats = {} }) {
  const [rpcSource, setRpcSource] = useState('MissionControl');
  const [rpcTarget, setRpcTarget] = useState('SAT-03');
  const [rpcMethod, setRpcMethod] = useState('GetHealth');
  const [rpcResult, setRpcResult] = useState(null);
  const [rpcLoading, setRpcLoading] = useState(false);

  const [p2pSource, setP2pSource] = useState('SAT-01');
  const [p2pTarget, setP2pTarget] = useState('SAT-04');
  const [p2pMessage, setP2pMessage] = useState('ORBITAL_HANDSHAKE: Telemetry sync request');
  const [p2pResult, setP2pResult] = useState(null);
  const [p2pLoading, setP2pLoading] = useState(false);

  const handleRunRpc = async () => {
    setRpcLoading(true);
    try {
      const res = await fetch('/api/rpc/invoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_satellite_id: rpcTarget,
          method: rpcMethod,
          timeout: 3.0
        })
      });
      const data = await res.json();
      setRpcResult(data);
    } catch (e) {
      setRpcResult({ success: false, error: str(e) });
    } finally {
      setRpcLoading(false);
    }
  };

  const handleSendP2p = async () => {
    setP2pLoading(true);
    try {
      const res = await fetch('/api/p2p/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_satellite_id: p2pSource,
          destination_satellite_id: p2pTarget,
          message_type: 'TELEMETRY_SYNC',
          payload: p2pMessage
        })
      });
      const data = await res.json();
      setP2pResult(data);
    } catch (e) {
      setP2pResult({ success: false, error: str(e) });
    } finally {
      setP2pLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100 font-orbitron">Distributed Communication Observatory</h2>
        <p className="text-xs text-slate-400 font-mono">
          Live inspection & execution of gRPC, RabbitMQ, WebSockets, P2P, and WebRTC protocols
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RPC gRPC Section */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-cyan-400 font-bold font-orbitron text-sm">
              <Zap className="w-4 h-4" />
              <span>Remote Procedure Call (RPC / gRPC)</span>
            </div>
            <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-300 rounded text-[10px] font-mono">
              proto/satellite.proto
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs font-mono">
            <div>
              <label className="text-slate-400 block mb-1">Source</label>
              <input value={rpcSource} disabled className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-slate-400" />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Target</label>
              <select value={rpcTarget} onChange={(e) => setRpcTarget(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200">
                <option value="SAT-01">SAT-01</option>
                <option value="SAT-02">SAT-02</option>
                <option value="SAT-03">SAT-03</option>
                <option value="SAT-04">SAT-04</option>
                <option value="SAT-05">SAT-05</option>
              </select>
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Method</label>
              <select value={rpcMethod} onChange={(e) => setRpcMethod(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200">
                <option value="GetHealth">GetHealth()</option>
                <option value="Ping">Ping()</option>
                <option value="GetSatelliteInfo">GetSatelliteInfo()</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleRunRpc}
            disabled={rpcLoading}
            className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2"
          >
            {rpcLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span>EXECUTE gRPC REQUEST</span>
          </button>

          {rpcResult && (
            <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-1">
                <span>Latency: <strong className="text-cyan-400">{rpcResult.latency_ms} ms</strong></span>
                <span className={rpcResult.success ? 'text-emerald-400' : 'text-rose-400'}>
                  {rpcResult.success ? 'SUCCESS' : 'FAILED'}
                </span>
              </div>
              <pre className="text-[11px] text-slate-300 overflow-x-auto max-h-40">{JSON.stringify(rpcResult, null, 2)}</pre>
            </div>
          )}
        </div>

        {/* P2P Messaging Section */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-indigo-400 font-bold font-orbitron text-sm">
              <Radio className="w-4 h-4" />
              <span>Direct Peer-to-Peer (P2P Satellite Messaging)</span>
            </div>
            <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded text-[10px] font-mono">
              Bypasses Mission Control
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            <div>
              <label className="text-slate-400 block mb-1">Source Node</label>
              <select value={p2pSource} onChange={(e) => setP2pSource(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200">
                <option value="SAT-01">SAT-01</option>
                <option value="SAT-02">SAT-02</option>
                <option value="SAT-03">SAT-03</option>
                <option value="SAT-04">SAT-04</option>
                <option value="SAT-05">SAT-05</option>
              </select>
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Destination Node</label>
              <select value={p2pTarget} onChange={(e) => setP2pTarget(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200">
                <option value="SAT-04">SAT-04</option>
                <option value="SAT-05">SAT-05</option>
                <option value="SAT-02">SAT-02</option>
                <option value="SAT-03">SAT-03</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-slate-400 block mb-1 text-xs font-mono">Payload Content</label>
            <input value={p2pMessage} onChange={(e) => setP2pMessage(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 text-xs font-mono" />
          </div>

          <button
            onClick={handleSendP2p}
            disabled={p2pLoading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2"
          >
            {p2pLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span>SEND DIRECT P2P MESSAGE</span>
          </button>

          {p2pResult && (
            <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-1">
                <span>Direct Link Latency: <strong className="text-indigo-400">{p2pResult.latency_ms} ms</strong></span>
                <span className={p2pResult.success ? 'text-emerald-400' : 'text-rose-400'}>
                  {p2pResult.success ? 'DELIVERED & ACKNOWLEDGED' : 'FAILED'}
                </span>
              </div>
              <pre className="text-[11px] text-slate-300 overflow-x-auto max-h-40">{JSON.stringify(p2pResult, null, 2)}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
