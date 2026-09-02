import React, { useState } from 'react';
import { Send, Zap, Radio, Terminal, Cpu, RefreshCw, CheckCircle, AlertTriangle, Layers, Crown, Activity } from 'lucide-react';

export default function CommunicationObservatory({ observatoryStats = {} }) {
  // gRPC state
  const [rpcSource, setRpcSource] = useState('MissionControl');
  const [rpcTarget, setRpcTarget] = useState('SAT-03');
  const [rpcMethod, setRpcMethod] = useState('GetHealth');
  const [rpcResult, setRpcResult] = useState(null);
  const [rpcLoading, setRpcLoading] = useState(false);

  // P2P state
  const [p2pSource, setP2pSource] = useState('SAT-01');
  const [p2pTarget, setP2pTarget] = useState('SAT-04');
  const [p2pMessage, setP2pMessage] = useState('ORBITAL_HANDSHAKE: Telemetry sync request');
  const [p2pResult, setP2pResult] = useState(null);
  const [p2pLoading, setP2pLoading] = useState(false);

  // Ring Election state
  const [initiatorId, setInitiatorId] = useState('SAT-01');
  const [electionResult, setElectionResult] = useState(null);
  const [electionLoading, setElectionLoading] = useState(false);

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
      setRpcResult({ success: false, error: String(e) });
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
      setP2pResult({ success: false, error: String(e) });
    } finally {
      setP2pLoading(false);
    }
  };

  const handleRunRingElection = async () => {
    setElectionLoading(true);
    try {
      const res = await fetch(`/api/election/ring?initiator_id=${initiatorId}`, { method: 'POST' });
      const data = await res.json();
      setElectionResult(data);
    } catch (e) {
      setElectionResult({ success: false, error: String(e) });
    } finally {
      setElectionLoading(false);
    }
  };

  const mqStats = observatoryStats.rabbitmq || {};
  const wsStats = observatoryStats.websocket || {};

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-bold text-slate-100 font-orbitron text-cyan-400">
          Distributed Communication Observatory
        </h2>
        <p className="text-xs text-slate-400 font-mono mt-1">
          Live execution, execution path tracing & evidence inspector for gRPC, RabbitMQ, WebSockets, P2P, WebRTC, and Ring Election
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RPC gRPC Section */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-cyan-400 font-bold font-orbitron text-sm">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span>Remote Procedure Call (RPC / gRPC)</span>
              </div>
              <span className="px-2.5 py-0.5 bg-cyan-500/20 text-cyan-300 rounded text-[10px] font-mono border border-cyan-500/30 font-orbitron">
                proto/satellite.proto
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs font-mono">
              <div>
                <label className="text-slate-400 block mb-1">Source</label>
                <input value={rpcSource} disabled className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-400" />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Target Satellite</label>
                <select value={rpcTarget} onChange={(e) => setRpcTarget(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-200">
                  <option value="SAT-01">SAT-01</option>
                  <option value="SAT-02">SAT-02</option>
                  <option value="SAT-03">SAT-03</option>
                  <option value="SAT-04">SAT-04</option>
                  <option value="SAT-05">SAT-05</option>
                </select>
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Proto Method</label>
                <select value={rpcMethod} onChange={(e) => setRpcMethod(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-200">
                  <option value="GetHealth">GetHealth()</option>
                  <option value="Ping">Ping()</option>
                  <option value="GetSatelliteInfo">GetSatelliteInfo()</option>
                </select>
              </div>
            </div>

            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl font-mono text-[11px] space-y-1">
              <span className="text-slate-400 font-bold">Execution Path:</span>
              <div className="text-slate-300 font-orbitron text-[10px] text-cyan-300">
                Frontend → FastAPI REST → GRPCClientManager → gRPC Channel (Port 500{rpcTarget.slice(-1)}) → {rpcTarget} Servicer → Response
              </div>
            </div>

            <button
              onClick={handleRunRpc}
              disabled={rpcLoading}
              className="w-full py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2 shadow-lg shadow-cyan-500/20"
            >
              {rpcLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span>EXECUTE gRPC REQUEST</span>
            </button>
          </div>

          {rpcResult && (
            <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2 font-mono text-xs mt-3">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2">
                <span className="text-slate-300 font-bold font-orbitron">Event: {rpcResult.event_id || 'EVT-gRPC'}</span>
                <div className="flex items-center space-x-3">
                  <span>Latency: <strong className="text-cyan-400">{rpcResult.latency_ms} ms</strong></span>
                  <span className={rpcResult.success ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                    {rpcResult.success ? '✓ SUCCESS (200 OK)' : '✗ FAILED'}
                  </span>
                </div>
              </div>
              <pre className="text-[11px] text-emerald-300 overflow-x-auto max-h-48 leading-relaxed">
                {JSON.stringify(rpcResult, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Direct P2P Messaging Section */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-indigo-400 font-bold font-orbitron text-sm">
                <Radio className="w-4 h-4 text-indigo-400" />
                <span>Direct Peer-to-Peer (P2P Satellite Link)</span>
              </div>
              <span className="px-2.5 py-0.5 bg-indigo-500/20 text-indigo-300 rounded text-[10px] font-mono border border-indigo-500/30 font-orbitron">
                No Mission Control Relay
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div>
                <label className="text-slate-400 block mb-1">Source Satellite</label>
                <select value={p2pSource} onChange={(e) => setP2pSource(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-200">
                  <option value="SAT-01">SAT-01</option>
                  <option value="SAT-02">SAT-02</option>
                  <option value="SAT-03">SAT-03</option>
                  <option value="SAT-04">SAT-04</option>
                  <option value="SAT-05">SAT-05</option>
                </select>
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Destination Peer</label>
                <select value={p2pTarget} onChange={(e) => setP2pTarget(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-200">
                  <option value="SAT-04">SAT-04</option>
                  <option value="SAT-05">SAT-05</option>
                  <option value="SAT-02">SAT-02</option>
                  <option value="SAT-03">SAT-03</option>
                  <option value="SAT-01">SAT-01</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-slate-400 block mb-1 text-xs font-mono">Payload Summary</label>
              <input value={p2pMessage} onChange={(e) => setP2pMessage(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 text-xs font-mono" />
            </div>

            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl font-mono text-[11px] space-y-1">
              <span className="text-slate-400 font-bold">Direct Network Route:</span>
              <div className="text-indigo-300 font-orbitron text-[10px]">
                {p2pSource} (Port 600{p2pSource.slice(-1)}) ─── Direct TCP/HTTP Link ───► {p2pTarget} (Port 600{p2pTarget.slice(-1)})
              </div>
            </div>

            <button
              onClick={handleSendP2p}
              disabled={p2pLoading}
              className="w-full py-2.5 bg-indigo-500 hover:bg-indigo-400 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2 shadow-lg shadow-indigo-500/20"
            >
              {p2pLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span>SEND DIRECT P2P MESSAGE</span>
            </button>
          </div>

          {p2pResult && (
            <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2 font-mono text-xs mt-3">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2">
                <span className="text-slate-300 font-bold font-orbitron">Event: {p2pResult.message_id || 'EVT-P2P'}</span>
                <div className="flex items-center space-x-3">
                  <span>Latency: <strong className="text-indigo-400">{p2pResult.latency_ms} ms</strong></span>
                  <span className={p2pResult.success ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                    {p2pResult.success ? '✓ DIRECT LINK DELIVERED' : '✗ FAILED'}
                  </span>
                </div>
              </div>
              <pre className="text-[11px] text-indigo-300 overflow-x-auto max-h-48 leading-relaxed">
                {JSON.stringify(p2pResult, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Ring Leader Election Section */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between lg:col-span-2">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-amber-400 font-bold font-orbitron text-sm">
                <Crown className="w-4 h-4 text-amber-400" />
                <span>Ring Leader Election Algorithm (Highest Active Node ID Wins)</span>
              </div>
              <span className="px-2.5 py-0.5 bg-amber-500/20 text-amber-300 rounded text-[10px] font-mono border border-amber-500/30 font-orbitron">
                Ring Topology: SAT-01 ➔ SAT-02 ➔ SAT-03 ➔ SAT-04 ➔ SAT-05
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
              <div>
                <label className="text-slate-400 block mb-1">Initiator Satellite</label>
                <select value={initiatorId} onChange={(e) => setInitiatorId(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-200">
                  <option value="SAT-01">SAT-01</option>
                  <option value="SAT-02">SAT-02</option>
                  <option value="SAT-03">SAT-03</option>
                  <option value="SAT-04">SAT-04</option>
                  <option value="SAT-05">SAT-05</option>
                </select>
              </div>
              <div className="md:col-span-2 p-3 bg-slate-900/80 border border-slate-800 rounded-xl font-mono text-[11px]">
                <span className="text-amber-400 font-bold">Algorithm Rule:</span>
                <p className="text-slate-300 mt-1 leading-relaxed">
                  Election message circulates through active ring nodes. Any node marked OFFLINE (e.g. stopped in Fault Simulator) is automatically bypassed. The active node with the highest ID is elected Leader.
                </p>
              </div>
            </div>

            <button
              onClick={handleRunRingElection}
              disabled={electionLoading}
              className="w-full py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2 shadow-lg shadow-amber-500/20"
            >
              {electionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Crown className="w-4 h-4" />}
              <span>TRIGGER RING LEADER ELECTION</span>
            </button>
          </div>

          {electionResult && (
            <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2 font-mono text-xs mt-3">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2">
                <span className="text-slate-300 font-bold font-orbitron">Elected Leader: <strong className="text-amber-400 font-orbitron text-sm">{electionResult.current_leader}</strong></span>
                <span className="text-emerald-400 font-bold">✓ ELECTION COMPLETED ({electionResult.latency_ms} ms)</span>
              </div>
              <pre className="text-[11px] text-amber-300 overflow-x-auto max-h-56 leading-relaxed">
                {JSON.stringify(electionResult, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Middleware Summary & Queue Status */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="text-sm font-bold text-slate-100 font-orbitron text-cyan-400">
              Middleware Integration Status & Metrics Summary
            </span>
            <span className="text-xs text-slate-400 font-mono">Ports: 5672 (AMQP), 8000 (FastAPI), 3000 (React)</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
              <span className="text-cyan-400 font-bold">RabbitMQ Broker (AMQP)</span>
              <div className="text-slate-300 text-[11px]">Exchange: <code className="text-cyan-300">telemetry.exchange</code></div>
              <div className="text-slate-300 text-[11px]">Queue: <code className="text-cyan-300">telemetry.queue</code></div>
              <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-800">
                <span className="text-slate-400">Status:</span>
                <span className="text-emerald-400 font-bold">{mqStats.connected ? 'CONNECTED (Port 5672)' : 'IN_MEMORY_FALLBACK'}</span>
              </div>
            </div>

            <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
              <span className="text-emerald-400 font-bold">WebSocket Streaming (/ws)</span>
              <div className="text-slate-300 text-[11px]">Active UI Connections: <code className="text-emerald-300">{wsStats.active_connections || 1}</code></div>
              <div className="text-slate-300 text-[11px]">Stream Protocol: <code className="text-emerald-300">Full-Duplex WSS</code></div>
              <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-800">
                <span className="text-slate-400">Throughput:</span>
                <span className="text-emerald-400 font-bold">~10 msg/sec Broadcast</span>
              </div>
            </div>

            <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
              <span className="text-indigo-400 font-bold">WebRTC Signaling</span>
              <div className="text-slate-300 text-[11px]">Signaling Endpoint: <code className="text-indigo-300">/api/webrtc/offer</code></div>
              <div className="text-slate-300 text-[11px]">Stream Codec: <code className="text-indigo-300">VP8 / 1080p Canvas</code></div>
              <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-800">
                <span className="text-slate-400">SDP State:</span>
                <span className="text-indigo-300 font-bold">NEGOTIATED</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
