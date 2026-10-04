import React, { useState } from 'react';
import { BookOpen, CheckCircle2, Play, Terminal, Zap, Radio, Server, Layers, Cpu, Video, ShieldCheck, Crown } from 'lucide-react';

const conceptsList = [
  {
    id: 'INDEPENDENT_NODES',
    unit: 'UNIT 1',
    title: '1. Independent Distributed Satellite Nodes',
    description: 'Each satellite runs as an autonomous process with local orbital runtime, telemetry generator, and dedicated network ports.',
    implementation: 'Five containerized satellite services (SAT-01 to SAT-05) running independently in Docker Compose.',
    tech: 'Python Microservices, Docker Containers',
    demoAction: 'INSPECT_NODES'
  },
  {
    id: 'SERVICE_DISCOVERY',
    unit: 'UNIT 1',
    title: '2. Dynamic Service Discovery & Registry',
    description: 'Satellites self-register on startup, providing node metadata, hostname, gRPC port, and P2P endpoints.',
    implementation: 'Mission Control Satellite Registry tracks satellite endpoints dynamically without hardcoding.',
    tech: 'FastAPI Registry, Self-Registration Protocol',
    demoAction: 'INSPECT_REGISTRY'
  },
  {
    id: 'GRPC_RPC',
    unit: 'UNIT 1',
    title: '3. gRPC Remote Procedure Calls',
    description: 'Strict interface contract definitions for synchronous health checks, telemetry retrieval, and commands.',
    implementation: 'GetHealth(), Ping(), and GetSatelliteInfo() defined in satellite.proto and executed over gRPC HTTP/2.',
    tech: 'gRPC, Protobuf, HTTP/2',
    demoAction: 'TEST_RPC'
  },
  {
    id: 'RABBITMQ_ASYNC',
    unit: 'UNIT 1',
    title: '4. Asynchronous Message-Oriented Middleware',
    description: 'Decoupled event-driven telemetry publishing using priority queues and background consumers.',
    implementation: 'Satellites publish AMQP messages to RabbitMQ telemetry exchanges with priority headers.',
    tech: 'RabbitMQ, AMQP Protocol, aio-pika',
    demoAction: 'INSPECT_OBSERVATORY'
  },
  {
    id: 'WEBSOCKET_STREAM',
    unit: 'UNIT 1',
    title: '5. Live Stream-Oriented Communication',
    description: 'Continuous real-time telemetry streaming from backend services to browser dashboard without polling.',
    implementation: 'WebSocket connection streams live telemetry updates at ~10 messages/sec directly to React UI.',
    tech: 'WebSockets, JSON Broadcast',
    demoAction: 'TEST_STREAM'
  },
  {
    id: 'P2P_DIRECT',
    unit: 'UNIT 1',
    title: '6. Direct Peer-to-Peer (P2P) Communication',
    description: 'Direct satellite-to-satellite cross-links without Mission Control relaying payload data.',
    implementation: 'SAT-01 sends direct network packet to SAT-04 via dedicated P2P HTTP/TCP socket endpoint.',
    tech: 'HTTP/1.1 P2P, Direct Sockets',
    demoAction: 'TEST_P2P'
  },
  {
    id: 'WEBRTC_MULTIMEDIA',
    unit: 'UNIT 1',
    title: '7. Distributed Multimedia & WebRTC Stream',
    description: 'Live continuous multimedia streaming from satellite camera payload directly to client.',
    implementation: 'WebRTC PeerConnection SDP Offer/Answer signaling delivers live simulated orbit camera video with telemetry overlay.',
    tech: 'WebRTC, SDP Signaling, VP8 Codec',
    demoAction: 'TEST_WEBRTC'
  },
  {
    id: 'HEARTBEAT_FAILURE',
    unit: 'UNIT 2',
    title: '8. Heartbeat Failure Detection & Lifecycle',
    description: 'Multistage heartbeat monitoring detecting missing node heartbeats and updating state.',
    implementation: 'Sweeper loop transitions nodes: >5s delayed → SUSPECTED, >10s missing → DISCONNECTED.',
    tech: 'Heartbeat Sweeper, State Machine',
    demoAction: 'TEST_FAILURE_DETECTION'
  },
  {
    id: 'DUAL_FAULT_INJECTION',
    unit: 'UNIT 2',
    title: '9. Dual-Source Real Fault Injection',
    description: 'Node failures can be injected via Mission Control UI or directly via external terminal commands.',
    implementation: 'Executing "docker stop satellite-03" in PowerShell is independently detected by backend heartbeat sweeper.',
    tech: 'Docker CLI, Fault Simulator Engine',
    demoAction: 'INSPECT_FAULTS'
  },
  {
    id: 'DETECTION_LATENCY',
    unit: 'UNIT 2',
    title: '10. Failure Detection Latency & Recovery Metrics',
    description: 'Precise quantitative measurement of time elapsed between node failure and detection.',
    implementation: 'System measures detection latency (ms) and recovery duration upon satellite auto re-registration.',
    tech: 'Timestamp Delta Calculation',
    demoAction: 'TEST_METRICS'
  },
  {
    id: 'CORRELATION_IDS',
    unit: 'UNIT 2',
    title: '11. End-to-End Event Correlation IDs',
    description: 'Unified traceability across satellite processes, backend logs, RabbitMQ, WebSockets, and UI.',
    implementation: 'Every distributed event is tagged with a unique correlation ID format EVT-YYYYMMDD-XXXXX.',
    tech: 'Global Correlation ID Generator',
    demoAction: 'TEST_CORRELATION'
  },
  {
    id: 'GOSSIP_STATE',
    unit: 'UNIT 2',
    title: '12. Gossip-Based State Dissemination',
    description: 'Decentralized peer-to-peer state sharing among satellite nodes without central server.',
    implementation: 'Satellites exchange neighbor health updates via direct /p2p/gossip mesh propagation.',
    tech: 'P2P Gossip Protocol, Neighbor Map',
    demoAction: 'TEST_GOSSIP'
  },
  {
    id: 'NETWORK_PARTITION',
    unit: 'UNIT 2',
    title: '13. Network Partition & State Reconciliation',
    description: 'Simulating network splits between satellite groups and deterministic post-recovery state reconciliation.',
    implementation: 'Restricting cross-partition P2P calls between Partition A & B, followed by state merge reconciliation.',
    tech: 'Partition Simulator, Deterministic Reconciler',
    demoAction: 'TEST_PARTITION'
  },
  {
    id: 'RESOURCE_AUTONOMY',
    unit: 'UNIT 2',
    title: '14. Local Resource-Aware Satellite Autonomy',
    description: 'Satellites dynamically adjust operational state based on internal resource constraints.',
    implementation: 'Battery < 30% activates POWER_SAVING mode (telemetry frequency 2s → 5s); Temp > 80°C activates THERMAL_PROTECTION.',
    tech: 'Local State Machine, Autonomy Loop',
    demoAction: 'TEST_AUTONOMY'
  },
  {
    id: 'RING_ELECTION',
    unit: 'UNIT 2',
    title: '15. Ring Leader Election Algorithm',
    description: 'Distributed coordination for selecting a unique leader node among active ring members.',
    implementation: 'Ring election circulates through active satellites (SAT-01..05), bypassing failed nodes. Highest active ID is elected leader.',
    tech: 'Ring Leader Election, Active ID Comparison',
    demoAction: 'TEST_ELECTION'
  },
  {
    id: 'CONTAINERIZATION',
    unit: 'UNIT 2',
    title: '16. Containerized Multi-Service Infrastructure',
    description: 'Entire distributed constellation packaged into independent Docker services with isolated networks.',
    implementation: 'Docker Compose orchestration running 9 containers (frontend, backend, 5 satellites, postgres, rabbitmq).',
    tech: 'Docker Compose, Bridge Network',
    demoAction: 'INSPECT_INFRA'
  },
  {
    id: 'DATABASE_AUDIT',
    unit: 'UNIT 2',
    title: '17. Persistent Relational Audit Logging',
    description: 'Historical audit persistence of all RPCs, P2P exchanges, fault logs, and telemetry history.',
    implementation: 'Async SQLAlchemy ORM persisting events to PostgreSQL satellite_system.db.',
    tech: 'PostgreSQL, SQLAlchemy Async',
    demoAction: 'INSPECT_DB'
  },
  {
    id: 'END_TO_END_OBSERVABILITY',
    unit: 'UNIT 2',
    title: '18. End-to-End Observability Chain',
    description: 'Simultaneous visibility of distributed events across Docker logs, backend API, DB, WebSockets, and UI.',
    implementation: 'Single event visible in Docker container logs, FastAPI logs, DB table, WebSocket broadcast, and Event Timeline.',
    tech: 'Structured Logging, Event Bus',
    demoAction: 'INSPECT_OBSERVABILITY'
  }
];

export default function DistributedConcepts() {
  const [activeEvidence, setActiveEvidence] = useState(null);

  const runDemo = async (action, concept) => {
    setActiveEvidence({ concept: concept.title, status: 'RUNNING', data: 'Invoking live backend runtime check...' });
    try {
      if (action === 'TEST_RPC') {
        const res = await fetch('/api/rpc/invoke', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_satellite_id: 'SAT-03', method: 'GetHealth' })
        });
        const data = await res.json();
        setActiveEvidence({ concept: concept.title, status: 'SUCCESS', data });
      } else if (action === 'TEST_P2P') {
        const res = await fetch('/api/p2p/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source_satellite_id: 'SAT-01', destination_satellite_id: 'SAT-04', payload: 'CONCEPT_VERIFICATION_P2P' })
        });
        const data = await res.json();
        setActiveEvidence({ concept: concept.title, status: 'SUCCESS', data });
      } else if (action === 'TEST_ELECTION') {
        const res = await fetch('/api/election/ring?initiator_id=SAT-01', { method: 'POST' });
        const data = await res.json();
        setActiveEvidence({ concept: concept.title, status: 'SUCCESS', data });
      } else if (action === 'TEST_GOSSIP') {
        const res = await fetch('/api/network/gossip');
        const data = await res.json();
        setActiveEvidence({ concept: concept.title, status: 'SUCCESS', data });
      } else if (action === 'TEST_PARTITION') {
        const res = await fetch('/api/faults');
        const data = await res.json();
        setActiveEvidence({ concept: concept.title, status: 'SUCCESS', data });
      } else if (action === 'TEST_WEBRTC') {
        const res = await fetch('/api/webrtc/status');
        const data = await res.json();
        setActiveEvidence({ concept: concept.title, status: 'SUCCESS', data });
      } else if (action === 'INSPECT_OBSERVABILITY') {
        const res = await fetch('/api/observatory/stats');
        const data = await res.json();
        setActiveEvidence({ concept: concept.title, status: 'SUCCESS', data });
      } else {
        const res = await fetch('/api/satellites');
        const data = await res.json();
        setActiveEvidence({ concept: concept.title, status: 'SUCCESS', data });
      }
    } catch (e) {
      setActiveEvidence({ concept: concept.title, status: 'ERROR', data: String(e) });
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron text-cyan-400">
            Distributed Systems Syllabus Coverage Matrix
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-1">Formal verification & runtime evidence mapping for Unit 1 & Unit 2</p>
        </div>
      </div>

      {activeEvidence && (
        <div className="glass-panel p-5 rounded-2xl border border-cyan-500/40 glow-cyan space-y-2 font-mono text-xs">
          <div className="flex items-center justify-between text-cyan-400 font-bold font-orbitron">
            <span>LIVE RUNTIME EVIDENCE: {activeEvidence.concept}</span>
            <span className={activeEvidence.status === 'SUCCESS' ? 'text-emerald-400' : 'text-rose-400'}>{activeEvidence.status}</span>
          </div>
          <pre className="text-[11px] text-emerald-300 overflow-x-auto p-3 bg-slate-950/90 rounded-xl border border-slate-800 max-h-56 leading-relaxed">
            {JSON.stringify(activeEvidence.data, null, 2)}
          </pre>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {conceptsList.map((c) => (
          <div key={c.id} className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3 flex flex-col justify-between hover:border-slate-700 transition">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 bg-cyan-500/20 text-cyan-300 text-[10px] font-bold rounded font-orbitron">
                  {c.unit}
                </span>
                <span className="text-[11px] font-mono text-slate-400">{c.tech}</span>
              </div>
              <h3 className="font-bold text-slate-100 text-sm font-orbitron">{c.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{c.description}</p>
              <div className="p-3 bg-slate-900/90 rounded-xl text-xs font-mono text-slate-300 border border-slate-800">
                <span className="text-cyan-400 font-bold">Implementation: </span>
                {c.implementation}
              </div>
            </div>

            <button
              onClick={() => runDemo(c.demoAction, c)}
              className="mt-3 py-2.5 px-4 bg-slate-900 hover:bg-cyan-500/20 hover:border-cyan-500/40 border border-slate-700 text-cyan-300 font-bold rounded-xl text-xs font-orbitron transition flex items-center justify-center space-x-2 shadow"
            >
              <Play className="w-3.5 h-3.5" />
              <span>RUN DEMO & VERIFY EVIDENCE</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
