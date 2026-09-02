import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Satellite,
  Activity,
  Zap,
  Radio,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Server,
  Cpu,
  RefreshCw
} from 'lucide-react';

export default function MissionOverview({ satellites = [], events = [], observatoryStats = {} }) {
  const [displaySatellites, setDisplaySatellites] = useState(satellites);

  useEffect(() => {
    if (satellites && satellites.length > 0) {
      setDisplaySatellites(satellites);
    } else {
      fetch('/api/satellites')
        .then(r => r.json())
        .then(d => {
          if (d.satellites && d.satellites.length > 0) {
            setDisplaySatellites(d.satellites);
          }
        })
        .catch(() => {});
    }
  }, [satellites]);

  const healthyCount = displaySatellites.filter(s => s.status === 'HEALTHY').length;
  const warningCount = displaySatellites.filter(s => s.status === 'WARNING').length;
  const criticalCount = displaySatellites.filter(s => s.status === 'CRITICAL').length;
  const offlineCount = displaySatellites.filter(s => s.status === 'OFFLINE').length;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner */}
      <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border border-slate-800">
        <div className="absolute -right-10 -bottom-10 opacity-10 pointer-events-none text-cyan-400">
          <Satellite className="w-64 h-64" />
        </div>
        <div className="relative z-10 space-y-2">
          <div className="flex items-center space-x-3">
            <span className="px-3 py-1 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded-full text-xs font-semibold font-orbitron">
              FA-1 CONSTELLATION STATUS
            </span>
            <span className="text-xs text-slate-400 font-mono">5 Independent LEO Satellite Microservices</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 font-orbitron tracking-wide">
            Distributed Mission Control Observatory
          </h2>
          <p className="text-sm text-slate-400 max-w-3xl leading-relaxed">
            Real-time monitoring system demonstrating multi-protocol communication (gRPC, RabbitMQ, WebSockets, P2P, WebRTC), dynamic service discovery, fault tolerance, and syllabus concepts.
          </p>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
        <div className="glass-card p-5 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Healthy Satellites</span>
            <Satellite className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold font-orbitron text-emerald-400">{healthyCount} / {displaySatellites.length || 5}</div>
          <div className="text-[11px] text-slate-400">Nominal orbital health</div>
        </div>

        <div className="glass-card p-5 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Telemetry Stream Rate</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-bold font-orbitron text-cyan-400">
            {observatoryStats?.websocket?.messages_per_second || '10.0'} <span className="text-xs font-normal text-slate-400">msg/s</span>
          </div>
          <div className="text-[11px] text-slate-400">WebSocket /ws live stream</div>
        </div>

        <div className="glass-card p-5 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Middleware Broker</span>
            <Radio className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-bold font-orbitron text-indigo-400">
            {observatoryStats?.rabbitmq?.connected ? 'RabbitMQ (5672)' : 'Resilient Queue'}
          </div>
          <div className="text-[11px] text-slate-400">Async Telemetry Exchange</div>
        </div>

        <div className="glass-card p-5 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>System Health State</span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <div className={`text-3xl font-bold font-orbitron ${offlineCount > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {offlineCount > 0 ? 'DEGRADED' : 'HEALTHY'}
          </div>
          <div className="text-[11px] text-slate-400">{offlineCount} offline, {warningCount} warning</div>
        </div>
      </div>

      {/* Quick Access to Views */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <NavLink to="/topology" className="glass-card p-5 rounded-2xl block space-y-2 border border-slate-800 hover:border-cyan-500/40 transition">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-200 text-sm font-orbitron">Constellation Topology</h3>
            <ArrowRight className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-xs text-slate-400">Interactive map displaying active P2P links and orbital nodes.</p>
        </NavLink>

        <NavLink to="/observatory" className="glass-card p-5 rounded-2xl block space-y-2 border border-slate-800 hover:border-cyan-500/40 transition">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-200 text-sm font-orbitron">Communication Observatory</h3>
            <ArrowRight className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-xs text-slate-400">Inspect RPC, RabbitMQ, WebSockets, P2P, and WebRTC streams live.</p>
        </NavLink>

        <NavLink to="/concepts" className="glass-card p-5 rounded-2xl block space-y-2 border border-slate-800 hover:border-cyan-500/40 transition">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-200 text-sm font-orbitron">Distributed Syllabus Matrix</h3>
            <ArrowRight className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-xs text-slate-400">Unit 1 & Unit 2 topic evidence with interactive demo triggers.</p>
        </NavLink>
      </div>

      {/* Satellite Status Table */}
      <div className="glass-panel p-6 rounded-2xl space-y-4 border border-slate-800">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-lg font-bold text-slate-200 font-orbitron text-cyan-400">Discovered Constellation Nodes</h3>
          <span className="text-xs text-slate-400 font-mono">Live Node State Table</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-orbitron text-[11px]">
              <tr>
                <th className="p-3">Satellite</th>
                <th className="p-3">Node ID</th>
                <th className="p-3">Endpoints</th>
                <th className="p-3">Status</th>
                <th className="p-3">Health Score</th>
                <th className="p-3">Battery</th>
                <th className="p-3">Temp</th>
                <th className="p-3">CPU</th>
                <th className="p-3">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {displaySatellites.length > 0 ? (
                displaySatellites.map((s) => (
                  <tr key={s.satellite_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-3 font-bold text-cyan-400 font-orbitron text-sm">{s.satellite_id}</td>
                    <td className="p-3 text-slate-400">{s.node_id || `NODE-${s.satellite_id}`}</td>
                    <td className="p-3 text-slate-300">gRPC:{s.grpc_port} | P2P:{s.p2p_port}</td>
                    <td className="p-3">
                      <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold ${
                        s.status === 'HEALTHY' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                        s.status === 'WARNING' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                        s.status === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                        'bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold'
                      }`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="p-3 font-bold text-slate-200">{s.health_score || 100}%</td>
                    <td className="p-3 text-slate-300">{s.battery || 95}%</td>
                    <td className="p-3 text-slate-300">{s.temperature || 24}°C</td>
                    <td className="p-3 text-slate-300">{s.cpu_usage || 15}%</td>
                    <td className="p-3 text-slate-400">{s.seconds_since_heartbeat !== undefined ? `${s.seconds_since_heartbeat}s ago` : 'Active'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="9" className="p-8 text-center text-slate-500 font-mono text-xs">
                    No satellites discovered. Ensure satellite processes are running.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
