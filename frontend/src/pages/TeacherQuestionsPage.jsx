import React, { useState } from 'react';
import { HelpCircle, CheckCircle2, ChevronRight, Terminal, Server, Zap, Radio, Video, Layers, ShieldCheck } from 'lucide-react';

const teacherQuestions = [
  {
    question: "Where is the distributed system?",
    frontendLoc: "Constellation Topology & Mission Overview pages",
    backendLoc: "satellites/satellite_node.py & backend/main.py",
    explanation: "The system consists of 5 independent satellite microservices (SAT-01 through SAT-05) running as separate processes/containers. Each node maintains its own local state, orbit telemetry, and endpoints, communicating across network sockets.",
    demoAction: "Show 5 distinct process ports (5001-5005, 6001-6005) or run 'docker compose ps'."
  },
  {
    question: "Where are the independent nodes?",
    frontendLoc: "Satellite Registry & Constellation Topology pages",
    backendLoc: "satellites/satellite_node.py",
    explanation: "Each satellite process (SAT-01 to SAT-05) executes its own autonomous orbit simulation loop, generating telemetry and heartbeats independently without central control.",
    demoAction: "Stop SAT-03 in Fault Simulator. Observe SAT-01, SAT-02, SAT-04, and SAT-05 continue operating normally."
  },
  {
    question: "Where is RPC (Remote Procedure Call)?",
    frontendLoc: "Communication Observatory -> gRPC Tab",
    backendLoc: "proto/satellite.proto & backend/communication/grpc_client.py",
    explanation: "Implemented using gRPC and Protocol Buffers. Methods include GetHealth(), Ping(), and GetSatelliteInfo().",
    demoAction: "Click 'EXECUTE gRPC REQUEST' to trigger a live GetHealth() RPC to SAT-03 and inspect latency (e.g. 14ms) and payload."
  },
  {
    question: "Where is message-oriented communication?",
    frontendLoc: "Communication Observatory & Mission Overview",
    backendLoc: "backend/communication/rabbitmq_manager.py",
    explanation: "Implemented using RabbitMQ AMQP message broker with telemetry.exchange fanout exchange and queues, with resilient in-memory fallback.",
    demoAction: "Inspect RabbitMQ message counters and JSON payload format."
  },
  {
    question: "Where is stream-oriented communication?",
    frontendLoc: "Live Telemetry Charts page",
    backendLoc: "backend/communication/websocket_manager.py",
    explanation: "Implemented using WebSockets. Continuous telemetry frames are broadcast at ~10 msg/sec to update React Recharts live.",
    demoAction: "Observe live continuous graph updates without page refreshes."
  },
  {
    question: "Where is Peer-to-Peer (P2P) communication?",
    frontendLoc: "Communication Observatory -> P2P Section",
    backendLoc: "satellites/satellite_node.py (/p2p/send_to_peer)",
    explanation: "Direct network link between SAT-01 and SAT-04. Mission Control only triggers the source satellite; SAT-01 opens a direct HTTP/socket connection to SAT-04 without passing through Mission Control relay.",
    demoAction: "Click 'SEND DIRECT P2P MESSAGE'. Verify relay status shows 'DIRECT_SATELLITE_TO_SATELLITE (No Mission Control Relay)'."
  },
  {
    question: "Where is WebRTC / Distributed Multimedia?",
    frontendLoc: "Satellite WebRTC Feed page",
    backendLoc: "backend/communication/webrtc_signaling.py",
    explanation: "Implemented via WebRTC PeerConnection with SDP Offer/Answer signaling to stream a simulated orbital camera feed.",
    demoAction: "Click 'ESTABLISH WEBRTC CONNECTION' and view the animated 1080p orbital video canvas."
  },
  {
    question: "Where are names, identifiers, and addresses?",
    frontendLoc: "Satellite Registry page",
    backendLoc: "backend/registry/service_registry.py",
    explanation: "The Satellite Registry maps human-readable names (SAT-01) to unique internal node IDs (NODE-SAT-01-xxxx), hostnames, gRPC ports, and P2P ports.",
    demoAction: "Open Satellite Registry table to view dynamic address resolution."
  },
  {
    question: "Where is fault tolerance and failure detection?",
    frontendLoc: "Fault Simulator page",
    backendLoc: "backend/registry/service_registry.py (sweep_failures)",
    explanation: "Satellites send heartbeats every 2s. If heartbeats stop for >10s (TTL), the registry marks the node OFFLINE. Remaining nodes continue operating.",
    demoAction: "Inject 'STOP_NODE' on SAT-03. Watch it transition to OFFLINE, then inject 'RESTART_NODE' to observe dynamic recovery."
  },
  {
    question: "Where is middleware?",
    frontendLoc: "Middleware Architecture page",
    backendLoc: "backend/communication/",
    explanation: "gRPC, RabbitMQ, WebSockets, and Service Registry form the middleware layer separating application UI from physical network sockets.",
    demoAction: "Open Middleware Architecture page to inspect the 4-layer abstraction diagram."
  },
  {
    question: "Where is virtualization?",
    frontendLoc: "Infrastructure / Docker view",
    backendLoc: "docker-compose.yml & docker/",
    explanation: "All 5 satellites, Mission Control backend, RabbitMQ broker, PostgreSQL database, and React frontend are containerized independently.",
    demoAction: "Run 'docker compose ps' in terminal."
  }
];

export default function TeacherQuestionsPage() {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const current = teacherQuestions[selectedIdx];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100 font-orbitron">Teacher Questions & Viva Evaluation Guide</h2>
        <p className="text-xs text-slate-400 font-mono">
          Direct evidence pointers & explanations for academic evaluation questions
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Questions Sidebar */}
        <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-2">
          <div className="text-xs font-bold text-cyan-400 uppercase tracking-wider font-orbitron px-2 py-1">
            Common Professor Questions
          </div>
          <div className="space-y-1">
            {teacherQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedIdx(idx)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-xs font-medium transition-all flex items-center justify-between ${
                  selectedIdx === idx
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <span className="truncate">{q.question}</span>
                <ChevronRight className="w-3.5 h-3.5 shrink-0 opacity-60" />
              </button>
            ))}
          </div>
        </div>

        {/* Answer Detail Card */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
          <div className="space-y-2 border-b border-slate-800 pb-4">
            <span className="px-2.5 py-0.5 bg-cyan-500/20 text-cyan-300 text-[10px] font-bold rounded font-orbitron">
              ACADEMIC VIVA DEFENSE
            </span>
            <h3 className="text-lg font-bold text-slate-100 font-orbitron text-cyan-400">{current.question}</h3>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-1">
              <span className="text-slate-400 font-bold">Explanation:</span>
              <p className="text-slate-200 leading-relaxed">{current.explanation}</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl space-y-1">
                <span className="text-cyan-400 font-bold">Frontend Location:</span>
                <div className="text-slate-300 font-orbitron">{current.frontendLoc}</div>
              </div>
              <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl space-y-1">
                <span className="text-indigo-400 font-bold">Backend Implementation:</span>
                <div className="text-slate-300">{current.backendLoc}</div>
              </div>
            </div>

            <div className="p-4 bg-cyan-950/40 border border-cyan-500/30 rounded-xl space-y-1">
              <span className="text-emerald-400 font-bold">Live Demonstration Procedure:</span>
              <p className="text-slate-300 font-orbitron">{current.demoAction}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
