import React, { useState, useEffect } from 'react';
import { Server, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';

export default function SatelliteRegistryPage({ satellites = [], onRefresh }) {
  const [registrySatellites, setRegistrySatellites] = useState(satellites);
  const [loading, setLoading] = useState(false);

  const fetchRegistryData = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/satellites');
      const data = await res.json();
      if (data.satellites) {
        setRegistrySatellites(data.satellites);
      }
    } catch (e) {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (satellites && satellites.length > 0) {
      setRegistrySatellites(satellites);
    } else {
      fetchRegistryData();
    }
  }, [satellites]);

  const handleRefreshClick = () => {
    if (onRefresh) onRefresh();
    fetchRegistryData();
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron text-cyan-400">
            Satellite Service Registry & Discovery
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Dynamic Name, Identifier, Address & Health TTL Discovery Lookup Table
          </p>
        </div>

        <button
          onClick={handleRefreshClick}
          disabled={loading}
          className="py-2.5 px-4 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-300 font-bold rounded-xl text-xs font-orbitron transition flex items-center space-x-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>REFRESH REGISTRY</span>
        </button>
      </div>

      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-orbitron text-[11px]">
              <tr>
                <th className="p-3.5">Satellite ID</th>
                <th className="p-3.5">Internal Node ID</th>
                <th className="p-3.5">Hostname</th>
                <th className="p-3.5">Address</th>
                <th className="p-3.5">gRPC Endpoint</th>
                <th className="p-3.5">P2P Endpoint</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Last Heartbeat</th>
                <th className="p-3.5">Capabilities</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {registrySatellites.length > 0 ? (
                registrySatellites.map((s) => (
                  <tr key={s.satellite_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-3.5 font-bold text-cyan-400 font-orbitron text-sm">{s.satellite_id}</td>
                    <td className="p-3.5 text-slate-400">{s.node_id || `NODE-${s.satellite_id}`}</td>
                    <td className="p-3.5 text-slate-300">{s.hostname || `${s.satellite_id.toLowerCase()}.orbital.local`}</td>
                    <td className="p-3.5 text-slate-300">{s.address || '127.0.0.1'}</td>
                    <td className="p-3.5 text-cyan-300 font-mono">:{s.grpc_port}</td>
                    <td className="p-3.5 text-indigo-300 font-mono">:{s.p2p_port}</td>
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
                    <td className="p-3.5 text-slate-400">{s.seconds_since_heartbeat !== undefined ? `${s.seconds_since_heartbeat}s ago` : 'Active'}</td>
                    <td className="p-3.5 text-slate-400 text-[10px]">
                      {(s.capabilities || ['TELEMETRY', 'gRPC', 'P2P', 'RABBITMQ', 'WEBRTC']).join(', ')}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="9" className="p-8 text-center text-slate-500 font-mono text-xs">
                    No satellites registered in SatelliteRegistry. Click REFRESH REGISTRY or ensure satellite processes are running.
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
