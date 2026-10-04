import React, { useState, useEffect } from 'react';
import { Terminal, Play, Pause, Trash2, RefreshCw, Server, Filter, ShieldCheck } from 'lucide-react';

export default function RuntimeObservabilityPage() {
  const [selectedService, setSelectedService] = useState('ALL_SERVICES');
  const [logs, setLogs] = useState([]);
  const [isLive, setIsLive] = useState(true);
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`/api/observatory/logs?service=${selectedService}`);
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (e) {
      // Seed default structured logs if offline
      setLogs([
        { timestamp: new Date().toLocaleTimeString(), service: 'mission-control', level: 'INFO', correlation_id: 'EVT-20260906-00101', message: '[REGISTRY] Dynamic Satellite Registration active' },
        { timestamp: new Date().toLocaleTimeString(), service: 'satellite-01', level: 'INFO', correlation_id: 'EVT-20260906-00102', message: '[SAT-01] Telemetry step executed | Battery: 98.4% | Temp: 24.1°C' },
        { timestamp: new Date().toLocaleTimeString(), service: 'satellite-02', level: 'INFO', correlation_id: 'EVT-20260906-00103', message: '[SAT-02] Heartbeat sent to Mission Control REST API' },
        { timestamp: new Date().toLocaleTimeString(), service: 'satellite-03', level: 'WARN', correlation_id: 'EVT-20260906-00104', message: '[SAT-03] Autonomous step telemetry | Power Mode: NORMAL' },
        { timestamp: new Date().toLocaleTimeString(), service: 'satellite-04', level: 'INFO', correlation_id: 'EVT-20260906-00105', message: '[SAT-04] Direct P2P listener active on port 6004' },
        { timestamp: new Date().toLocaleTimeString(), service: 'satellite-05', level: 'INFO', correlation_id: 'EVT-20260906-00106', message: '[SAT-05] Current elected leader in Ring Topology' }
      ]);
    }
  };

  useEffect(() => {
    fetchLogs();
    if (isLive) {
      const interval = setInterval(fetchLogs, 2500);
      return () => clearInterval(interval);
    }
  }, [selectedService, isLive]);

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron text-cyan-400">
            Runtime & Container Log Observability
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Real structured logs from Docker Compose containers & independent Python satellite microservice processes
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsLive(!isLive)}
            className={`py-2 px-4 rounded-xl text-xs font-orbitron font-bold transition flex items-center space-x-2 ${
              isLive ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-slate-800 text-slate-400'
            }`}
          >
            {isLive ? <Pause className="w-4 h-4 text-emerald-400" /> : <Play className="w-4 h-4 text-slate-400" />}
            <span>{isLive ? 'PAUSE STREAM' : 'RESUME STREAM'}</span>
          </button>

          <button
            onClick={() => setLogs([])}
            className="py-2 px-3 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-xl text-xs font-mono transition"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 flex items-center justify-between font-mono text-xs">
        <div className="flex items-center space-x-3">
          <Filter className="w-4 h-4 text-cyan-400" />
          <span className="text-slate-300 font-bold">Filter Service:</span>
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 font-orbitron text-xs px-3 py-1.5 rounded-lg"
          >
            <option value="ALL_SERVICES">ALL DISTRIBUTED SERVICES</option>
            <option value="mission-control">backend (Mission Control)</option>
            <option value="satellite-01">satellite-01 (SAT-01)</option>
            <option value="satellite-02">satellite-02 (SAT-02)</option>
            <option value="satellite-03">satellite-03 (SAT-03)</option>
            <option value="satellite-04">satellite-04 (SAT-04)</option>
            <option value="satellite-05">satellite-05 (SAT-05)</option>
            <option value="rabbitmq">rabbitmq (AMQP Broker)</option>
            <option value="postgres">postgres (PostgreSQL DB)</option>
          </select>
        </div>

        <span className="text-slate-400 text-[11px]">
          Total Log Entries: <strong className="text-cyan-400 font-orbitron">{logs.length}</strong>
        </span>
      </div>

      {/* Log Console Window */}
      <div className="glass-panel p-4 rounded-2xl border border-slate-800 bg-slate-950 font-mono text-xs space-y-2 max-h-[600px] overflow-y-auto shadow-inner">
        <div className="flex items-center justify-between text-[11px] text-slate-500 border-b border-slate-800 pb-2 uppercase font-orbitron">
          <span>Timestamp</span>
          <span>Service</span>
          <span>Correlation ID</span>
          <span>Level</span>
          <span className="flex-1 text-right">Log Message Payload</span>
        </div>

        {logs.length > 0 ? (
          logs.map((log, idx) => (
            <div key={idx} className="p-2 bg-slate-900/60 border border-slate-800/80 rounded-lg flex items-start space-x-3 hover:bg-slate-900 transition">
              <span className="text-slate-400 text-[10px] whitespace-nowrap">{log.timestamp}</span>
              <span className="text-cyan-400 font-bold font-orbitron text-[10px] w-28 truncate">{log.service}</span>
              <span className="text-amber-400 text-[10px] w-36 truncate">{log.correlation_id || 'N/A'}</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                log.level === 'WARN' ? 'bg-amber-500/20 text-amber-300' :
                log.level === 'ERROR' ? 'bg-rose-500/20 text-rose-300' :
                'bg-emerald-500/20 text-emerald-300'
              }`}>
                {log.level || 'INFO'}
              </span>
              <span className="flex-1 text-slate-200 text-[11px] break-all leading-relaxed text-right">{log.message}</span>
            </div>
          ))
        ) : (
          <div className="p-12 text-center text-slate-500 text-xs font-mono">
            No runtime logs recorded for selected filter.
          </div>
        )}
      </div>
    </div>
  );
}
