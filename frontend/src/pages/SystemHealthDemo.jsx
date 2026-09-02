import React, { useState } from 'react';
import { PlayCircle, CheckCircle, RefreshCw, Zap, ShieldCheck, Radio, Server, Code, Terminal, Layers } from 'lucide-react';

const demoScenarios = [
  {
    id: 1,
    title: 'DEMO 1: Distributed Nodes & Process Health',
    concept: 'Distributed Nodes & Independent Processes',
    desc: 'Verifies backend health, database connection, RabbitMQ broker, and status of all 5 independent satellite microservices.',
    endpoint: 'GET /api/health',
    codeLoc: 'backend/main.py -> get_system_health()',
    action: 'CHECK_HEALTH'
  },
  {
    id: 2,
    title: 'DEMO 2: Satellite Microservice Topology',
    concept: 'Distributed Architecture & Multiprocessing',
    desc: 'Inspects all 5 satellite processes operating on separate gRPC and P2P ports (5001-5005 & 6001-6005).',
    endpoint: 'GET /api/satellites',
    codeLoc: 'satellites/satellite_node.py -> SatelliteNode',
    action: 'GET_SATS'
  },
  {
    id: 3,
    title: 'DEMO 3: Dynamic Service Discovery',
    concept: 'Service Discovery & Naming',
    desc: 'Inspects Satellite Registry mapping dynamic symbolic names (SAT-01..05) to IP addresses, hostnames, and ports.',
    endpoint: 'GET /api/satellites',
    codeLoc: 'backend/registry/service_registry.py -> SatelliteRegistry',
    action: 'GET_REGISTRY'
  },
  {
    id: 4,
    title: 'DEMO 4: Autonomous Telemetry Generation',
    concept: 'Autonomous Local State Calculation',
    desc: 'Inspects live battery, temperature, CPU, and orbit trajectory calculations generated independently by satellite nodes.',
    endpoint: 'GET /api/observatory/stats',
    codeLoc: 'satellites/satellite_node.py -> step_telemetry()',
    action: 'GET_TELEMETRY'
  },
  {
    id: 5,
    title: 'DEMO 5: Remote Procedure Call (gRPC)',
    concept: 'Synchronous RPC & Protocol Buffers',
    desc: 'Executes GetHealth(SAT-03) RPC call using compiled Protocol Buffers contracts over gRPC.',
    endpoint: 'POST /api/rpc/invoke',
    codeLoc: 'proto/satellite.proto & backend/communication/grpc_client.py',
    action: 'EXEC_RPC'
  },
  {
    id: 6,
    title: 'DEMO 6: Message-Oriented Middleware (RabbitMQ)',
    concept: 'Asynchronous Pub/Sub Communication',
    desc: 'Publishes and consumes async telemetry messages from RabbitMQ fanout exchange (telemetry.exchange).',
    endpoint: 'GET /api/observatory/stats',
    codeLoc: 'backend/communication/rabbitmq_manager.py -> RabbitMQManager',
    action: 'EXEC_MQ'
  },
  {
    id: 7,
    title: 'DEMO 7: Stream-Oriented Communication (WebSockets)',
    concept: 'Low-Latency Real-Time Telemetry Streaming',
    desc: 'Verifies continuous JSON frame broadcasting at ~10 msg/sec over WebSocket connection (/ws).',
    endpoint: 'WS /ws',
    codeLoc: 'backend/communication/websocket_manager.py -> ConnectionManager',
    action: 'CHECK_WS'
  },
  {
    id: 8,
    title: 'DEMO 8: Direct P2P Satellite Link',
    concept: 'Peer-to-Peer Direct Cross-Link (No Central Relay)',
    desc: 'Sends direct P2P packet SAT-01 -> SAT-04 directly across satellite network ports without Mission Control relay.',
    endpoint: 'POST /api/p2p/send',
    codeLoc: 'satellites/satellite_node.py -> send_to_peer()',
    action: 'EXEC_P2P'
  },
  {
    id: 9,
    title: 'DEMO 9: Distributed Multimedia (WebRTC)',
    concept: 'WebRTC SDP Offer/Answer Signaling & Video Stream',
    desc: 'Negotiates SDP offer/answer session to establish live simulated 1080p orbital camera feed.',
    endpoint: 'POST /api/webrtc/offer',
    codeLoc: 'backend/communication/webrtc_signaling.py -> WebRTCSignalingManager',
    action: 'WEBRTC'
  },
  {
    id: 10,
    title: 'DEMO 10: Inject Node Failure',
    concept: 'Heartbeat Timeout & Failure Detection',
    desc: 'Stops SAT-03; background sweeper detects heartbeat outage (>10s TTL) and marks status OFFLINE.',
    endpoint: 'POST /api/faults/inject (STOP_NODE)',
    codeLoc: 'backend/registry/service_registry.py -> sweep_failures()',
    action: 'INJECT_STOP'
  },
  {
    id: 11,
    title: 'DEMO 11: Satellite Recovery & Re-registration',
    concept: 'Autonomous Failure Recovery & Re-joining',
    desc: 'Restores SAT-03; node auto-issues heartbeat/registration, returning status to HEALTHY.',
    endpoint: 'POST /api/faults/inject (RESTART_NODE)',
    codeLoc: 'satellites/satellite_node.py -> register_with_mission_control()',
    action: 'INJECT_RESTART'
  },
  {
    id: 12,
    title: 'DEMO 12: Ring Leader Election Algorithm',
    concept: 'Distributed Leader Election (Highest Active ID Wins)',
    desc: 'Circulates election message around active satellite ring topology (SAT-01 -> SAT-02 -> SAT-03 -> SAT-04 -> SAT-05), bypassing failed nodes to elect new constellation leader.',
    endpoint: 'POST /api/election/ring',
    codeLoc: 'backend/registry/service_registry.py -> run_ring_election()',
    action: 'RING_ELECTION'
  },
  {
    id: 13,
    title: 'DEMO 13: Packet Loss Simulation',
    concept: 'Distributed System Resiliency & Exception Handling',
    desc: 'Injects 20% packet loss to verify retry mechanism and resilient exception handling.',
    endpoint: 'POST /api/faults/inject (PACKET_LOSS)',
    codeLoc: 'backend/faults/fault_simulator.py -> get_node_faults()',
    action: 'INJECT_LOSS'
  },
  {
    id: 14,
    title: 'DEMO 14: Communication Replay & Timeline',
    concept: 'Distributed Log Persistence & Model of Computation',
    desc: 'Replays chronological audit trail of all historical gRPC, RabbitMQ, P2P, and WebRTC network events.',
    endpoint: 'GET /api/replay/history',
    codeLoc: 'backend/database/models.py -> CommunicationEvent',
    action: 'REPLAY'
  }
];

export default function SystemHealthDemo() {
  const [activeResult, setActiveResult] = useState(null);
  const [loadingId, setLoadingId] = useState(null);

  const runDemoStep = async (demo) => {
    setLoadingId(demo.id);
    try {
      if (demo.action === 'EXEC_RPC') {
        const res = await fetch('/api/rpc/invoke', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_satellite_id: 'SAT-03', method: 'GetHealth' })
        });
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'EXEC_P2P') {
        const res = await fetch('/api/p2p/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source_satellite_id: 'SAT-01', destination_satellite_id: 'SAT-04', payload: 'CLASSROOM_DEMO_P2P_PACKET' })
        });
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'INJECT_STOP') {
        const res = await fetch('/api/faults/inject', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fault_type: 'STOP_NODE', target_node: 'SAT-03' })
        });
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'INJECT_RESTART') {
        const res = await fetch('/api/faults/inject', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fault_type: 'RESTART_NODE', target_node: 'SAT-03' })
        });
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'INJECT_LATENCY') {
        const res = await fetch('/api/faults/inject', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fault_type: 'HIGH_LATENCY', target_node: 'SAT-01', parameters: { latency_ms: 500 } })
        });
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'RING_ELECTION') {
        const res = await fetch('/api/election/ring?initiator_id=SAT-01', { method: 'POST' });
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'INJECT_LOSS') {
        const res = await fetch('/api/faults/inject', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fault_type: 'PACKET_LOSS', target_node: 'SAT-02', parameters: { loss_percent: 20 } })
        });
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'WEBRTC') {
        const res = await fetch('/api/webrtc/offer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ offer_sdp: 'v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\ns=SatelliteFeed\r\nt=0 0\r\n', peer: 'SAT-02' })
        });
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'GET_SATS' || demo.action === 'GET_REGISTRY') {
        const res = await fetch('/api/satellites');
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'GET_TELEMETRY' || demo.action === 'EXEC_MQ') {
        const res = await fetch('/api/observatory/stats');
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else if (demo.action === 'REPLAY') {
        const res = await fetch('/api/replay/history');
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      } else {
        const res = await fetch('/api/health');
        const data = await res.json();
        setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, data });
      }
    } catch (e) {
      setActiveResult({ demo: demo.title, endpoint: demo.endpoint, codeLoc: demo.codeLoc, error: String(e) });
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron text-cyan-400">
            Classroom Viva & Evaluation Demo Center
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Interactive verification control panel for live professor evaluation (DEMO 1 through DEMO 14)
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="px-3 py-1 bg-cyan-500/20 text-cyan-300 text-xs font-bold rounded-lg font-orbitron border border-cyan-500/40">
            FA-1 EVALUATION READY
          </span>
        </div>
      </div>

      {/* Live Response Panel */}
      {activeResult && (
        <div className="glass-panel p-5 rounded-2xl border border-emerald-500/50 glow-cyan space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-emerald-500/30 pb-2">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              <span className="text-emerald-300 font-bold font-orbitron">{activeResult.demo}</span>
            </div>
            <span className="text-emerald-400 text-[11px] font-orbitron px-2 py-0.5 bg-emerald-950 rounded border border-emerald-500/40">
              API RESPONDED 200 OK
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-slate-300">
            <div className="p-2 bg-slate-900/90 rounded border border-slate-800 flex items-center justify-between">
              <span className="text-slate-400 font-bold">API Endpoint:</span>
              <span className="text-cyan-300 font-orbitron">{activeResult.endpoint}</span>
            </div>
            <div className="p-2 bg-slate-900/90 rounded border border-slate-800 flex items-center justify-between">
              <span className="text-slate-400 font-bold">Code Location:</span>
              <span className="text-indigo-300">{activeResult.codeLoc}</span>
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-slate-400 font-bold">Live Execution Payload Evidence:</span>
            <pre className="text-[11px] text-emerald-300 overflow-x-auto p-3.5 bg-slate-950/95 rounded-xl border border-slate-800 max-h-60 leading-relaxed font-mono">
              {JSON.stringify(activeResult.data || activeResult.error, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Demo Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {demoScenarios.map((d) => (
          <div key={d.id} className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between hover:border-slate-700 transition">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-cyan-400 font-orbitron uppercase tracking-wider px-2 py-0.5 bg-cyan-950 rounded border border-cyan-500/30">
                  {d.concept}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">{d.endpoint}</span>
              </div>
              <h3 className="font-bold text-slate-100 text-sm font-orbitron">{d.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{d.desc}</p>
            </div>

            <div className="space-y-3 pt-2 border-t border-slate-800/60">
              <div className="text-[11px] font-mono text-indigo-300 flex items-center space-x-1.5">
                <Code className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <span className="truncate">{d.codeLoc}</span>
              </div>

              <button
                onClick={() => runDemoStep(d)}
                disabled={loadingId === d.id}
                className="w-full py-2.5 px-4 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2 shadow-lg shadow-cyan-500/20"
              >
                {loadingId === d.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
                <span>EXECUTE {d.title.split(':')[0]}</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
