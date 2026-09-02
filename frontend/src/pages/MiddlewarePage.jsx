import React from 'react';
import { Layers, Zap, Radio, Server, Network, Terminal } from 'lucide-react';

export default function MiddlewarePage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100 font-orbitron">Middleware Architecture Visualization</h2>
        <p className="text-xs text-slate-400 font-mono">
          Layered software abstraction model separating application logic from network protocols
        </p>
      </div>

      <div className="glass-panel p-8 rounded-2xl border border-slate-800 space-y-6">
        {/* Layer 1: Application Layer */}
        <div className="p-5 bg-cyan-950/30 border border-cyan-500/40 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-cyan-400 font-bold font-orbitron text-sm">
            <span>1. APPLICATION LAYER</span>
            <span>Mission Control & Telemetry Dashboard</span>
          </div>
          <p className="text-xs text-slate-300">
            React Mission Control UI, Telemetry Analytics Engine, Health Monitor, Fault Recovery Orchestrator.
          </p>
        </div>

        <div className="text-center text-slate-600 font-mono text-xs font-bold">↓ Communication Abstraction API ↓</div>

        {/* Layer 2: Middleware Layer */}
        <div className="p-6 bg-slate-900/90 border border-indigo-500/40 rounded-xl space-y-4 glow-indigo">
          <div className="flex items-center justify-between text-indigo-400 font-bold font-orbitron text-sm">
            <span>2. MIDDLEWARE SYSTEM LAYER</span>
            <span>Distributed Messaging & RPC Primitives</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
              <span className="text-cyan-400 font-bold">gRPC Middleware</span>
              <p className="text-[11px] text-slate-400">Protobuf RPCs for GetHealth(), GetTelemetry(), Ping()</p>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
              <span className="text-amber-400 font-bold">RabbitMQ AMQP</span>
              <p className="text-[11px] text-slate-400">Decoupled pub/sub telemetry exchange & event queues</p>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
              <span className="text-emerald-400 font-bold">WebSocket Stream</span>
              <p className="text-[11px] text-slate-400">Low-latency JSON frame telemetry broadcaster</p>
            </div>
          </div>
        </div>

        <div className="text-center text-slate-600 font-mono text-xs font-bold">↓ Network Protocols ↓</div>

        {/* Layer 3: Network Layer */}
        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-slate-300 font-bold font-orbitron text-sm">
            <span>3. NETWORK & PHYSICAL LAYER</span>
            <span>TCP / IP / Sockets / WebRTC DataChannels</span>
          </div>
          <p className="text-xs text-slate-400">
            HTTP/2, TCP Sockets, AMQP 0-9-1, UDP/SRTP WebRTC Media Channels.
          </p>
        </div>

        <div className="text-center text-slate-600 font-mono text-xs font-bold">↓ Distributed Execution ↓</div>

        {/* Layer 4: Satellite Microservices */}
        <div className="p-5 bg-slate-900/80 border border-cyan-500/30 rounded-xl flex justify-between items-center font-mono text-xs">
          <span className="text-slate-300 font-bold font-orbitron">4. DISTRIBUTED NODES:</span>
          <span className="text-cyan-400">SAT-01</span>
          <span className="text-cyan-400">SAT-02</span>
          <span className="text-cyan-400">SAT-03</span>
          <span className="text-cyan-400">SAT-04</span>
          <span className="text-cyan-400">SAT-05</span>
        </div>
      </div>
    </div>
  );
}
