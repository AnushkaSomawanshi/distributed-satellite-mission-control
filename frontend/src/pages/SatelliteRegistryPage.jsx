import React from 'react';
import { Server, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';

export default function SatelliteRegistryPage({ satellites = [], onRefresh }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron">Satellite Service Registry</h2>
          <p className="text-xs text-slate-400 font-mono">
            Dynamic Name, Identifier, Address & Health TTL Discovery Lookup Table
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="py-2 px-4 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-xl text-xs font-orbitron transition flex items-center space-x-2 border border-slate-700"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>REFRESH REGISTRY</span>
        </button>
      </div>

      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/90 text-slate-400 uppercase">
              <tr>
                <th className="p-3.5">Satellite ID</th>
                <th className="p-3.5">Internal Node ID</th>
                <th className="p-3.5">Hostname</th>
                <th className="p-3.5">Address</th>
                <th className="p-3.5">gRPC Endpoint</th>
                <th className="p-3.5">P2P Endpoint</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Last Seen</th>
                <th className="p-3.5">Capabilities</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {satellites.map((s) => (
                <tr key={s.satellite_id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3.5 font-bold text-cyan-400 font-orbitron">{s.satellite_id}</td>
                  <td className="p-3.5 text-slate-400">{s.node_id}</td>
                  <td className="p-3.5 text-slate-300">{s.hostname}</td>
                  <td className="p-3.5 text-slate-300">{s.address}</td>
                  <td className="p-3.5 text-slate-200">:{s.grpc_port}</td>
                  <td className="p-3.5 text-slate-200">:{s.p2p_port}</td>
                  <td className="p-3.5">
                    <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold ${
                      s.status === 'HEALTHY' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                      s.status === 'WARNING' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                      s.status === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                      'bg-slate-700/50 text-slate-400 border border-slate-600'
                    }`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="p-3.5 text-slate-400">{s.seconds_since_heartbeat || 0}s ago</td>
                  <td className="p-3.5 text-slate-400 text-[10px]">
                    {(s.capabilities || ['TELEMETRY', 'gRPC', 'P2P']).join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
