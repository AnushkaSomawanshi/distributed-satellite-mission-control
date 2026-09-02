import React, { useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import { Activity, Battery, Thermometer, Cpu, Radio, ShieldAlert, HeartPulse } from 'lucide-react';

export default function LiveTelemetryPage({ telemetryHistory = [], satellites = [] }) {
  const [selectedSatellite, setSelectedSatellite] = useState('ALL');

  const sat02Status = satellites.find(s => s.satellite_id === 'SAT-02')?.status || 'HEALTHY';

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 font-orbitron text-cyan-400">
            Live Stream-Oriented Telemetry Charts
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Real-time full-duplex WebSocket stream (/ws) broadcasting battery, solar temperature, CPU, and health score metrics
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="font-mono text-xs text-slate-400 flex items-center space-x-2">
            <span>Filter Satellite:</span>
            <select
              value={selectedSatellite}
              onChange={(e) => setSelectedSatellite(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-slate-200 font-orbitron text-xs"
            >
              <option value="ALL">All Satellites (SAT-01..05)</option>
              <option value="SAT-01">SAT-01</option>
              <option value="SAT-02">SAT-02</option>
              <option value="SAT-03">SAT-03</option>
              <option value="SAT-04">SAT-04</option>
              <option value="SAT-05">SAT-05</option>
            </select>
          </div>

          <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 text-xs font-bold rounded-lg font-orbitron border border-emerald-500/40 flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping mr-1"></span>
            <span>WEBSOCKET LIVE</span>
          </span>
        </div>
      </div>

      {sat02Status === 'OFFLINE' && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center justify-between text-xs font-mono text-rose-300">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <strong className="font-orbitron text-rose-200">NODE FAILURE DETECTED: SAT-02 IS OFFLINE</strong>
              <p className="text-[11px] text-rose-400">Heartbeat timeout (&gt;10s). SAT-02 telemetry stream is HALTED. Other satellite streams continue operating nominal.</p>
            </div>
          </div>
          <span className="px-2.5 py-1 bg-rose-500/20 rounded font-bold">STREAM HALTED</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Battery Telemetry */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 font-orbitron flex items-center space-x-2">
              <Battery className="w-4 h-4 text-emerald-400" />
              <span>Battery Charge Level (% Solar Eclipse Cycle)</span>
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">0 - 100%</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-01') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-01_battery" stroke="#10b981" strokeWidth={2.5} dot={true} name="SAT-01" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-02') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-02_battery" stroke="#f43f5e" strokeWidth={2.5} dot={true} name="SAT-02" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-03') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-03_battery" stroke="#06b6d4" strokeWidth={2.5} dot={true} name="SAT-03" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-04') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-04_battery" stroke="#8b5cf6" strokeWidth={2.5} dot={true} name="SAT-04" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-05') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-05_battery" stroke="#f59e0b" strokeWidth={2.5} dot={true} name="SAT-05" />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Temperature Telemetry */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 font-orbitron flex items-center space-x-2">
              <Thermometer className="w-4 h-4 text-amber-400" />
              <span>Satellite Core Temperature (°C)</span>
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">0 - 90°C</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis domain={[0, 90]} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-01') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-01_temp" stroke="#10b981" strokeWidth={2.5} dot={true} name="SAT-01" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-02') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-02_temp" stroke="#f43f5e" strokeWidth={2.5} dot={true} name="SAT-02" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-03') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-03_temp" stroke="#06b6d4" strokeWidth={2.5} dot={true} name="SAT-03" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-04') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-04_temp" stroke="#8b5cf6" strokeWidth={2.5} dot={true} name="SAT-04" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-05') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-05_temp" stroke="#f59e0b" strokeWidth={2.5} dot={true} name="SAT-05" />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: CPU Workload */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 font-orbitron flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>Processor Utilization & Workload Load (%)</span>
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">0 - 100% Load</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-01') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-01_cpu" stroke="#10b981" strokeWidth={2.5} dot={true} name="SAT-01" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-02') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-02_cpu" stroke="#f43f5e" strokeWidth={2.5} dot={true} name="SAT-02" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-03') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-03_cpu" stroke="#06b6d4" strokeWidth={2.5} dot={true} name="SAT-03" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-04') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-04_cpu" stroke="#8b5cf6" strokeWidth={2.5} dot={true} name="SAT-04" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-05') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-05_cpu" stroke="#f59e0b" strokeWidth={2.5} dot={true} name="SAT-05" />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Health Score vs Time */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 font-orbitron flex items-center space-x-2">
              <HeartPulse className="w-4 h-4 text-rose-400" />
              <span>Calculated Health Score (% Overall State)</span>
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">0 - 100 Health Score</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-01') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-01_health" stroke="#10b981" strokeWidth={2.5} dot={true} name="SAT-01" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-02') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-02_health" stroke="#f43f5e" strokeWidth={2.5} dot={true} name="SAT-02" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-03') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-03_health" stroke="#06b6d4" strokeWidth={2.5} dot={true} name="SAT-03" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-04') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-04_health" stroke="#8b5cf6" strokeWidth={2.5} dot={true} name="SAT-04" />
                )}
                {(selectedSatellite === 'ALL' || selectedSatellite === 'SAT-05') && (
                  <Line type="monotone" connectNulls={true} dataKey="SAT-05_health" stroke="#f59e0b" strokeWidth={2.5} dot={true} name="SAT-05" />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
