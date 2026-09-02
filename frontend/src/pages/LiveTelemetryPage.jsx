import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Activity, Battery, Thermometer, Cpu } from 'lucide-react';

export default function LiveTelemetryPage({ telemetryHistory = [], satellites = [] }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100 font-orbitron">Live Telemetry Charts</h2>
        <p className="text-xs text-slate-400 font-mono">
          Continuous WebSocket streaming data for Battery, Solar Temperature, CPU, and Signal Strength
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Battery Telemetry */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 font-orbitron flex items-center space-x-2">
              <Battery className="w-4 h-4 text-emerald-400" />
              <span>Battery Level (% Solar Eclipse Cycle)</span>
            </h3>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Line type="monotone" dataKey="SAT-01_battery" stroke="#10b981" strokeWidth={2} dot={false} name="SAT-01 Battery" />
                <Line type="monotone" dataKey="SAT-02_battery" stroke="#06b6d4" strokeWidth={2} dot={false} name="SAT-02 Battery" />
                <Line type="monotone" dataKey="SAT-03_battery" stroke="#8b5cf6" strokeWidth={2} dot={false} name="SAT-03 Battery" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Temperature Telemetry */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 font-orbitron flex items-center space-x-2">
              <Thermometer className="w-4 h-4 text-amber-400" />
              <span>Satellite Core Temperature (°C)</span>
            </h3>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis domain={[0, 90]} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Line type="monotone" dataKey="SAT-01_temp" stroke="#f59e0b" strokeWidth={2} dot={false} name="SAT-01 Temp" />
                <Line type="monotone" dataKey="SAT-02_temp" stroke="#ec4899" strokeWidth={2} dot={false} name="SAT-02 Temp" />
                <Line type="monotone" dataKey="SAT-03_temp" stroke="#3b82f6" strokeWidth={2} dot={false} name="SAT-03 Temp" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* CPU & Workload */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 font-orbitron flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>Processor Load & Telemetry Stream Rate (%)</span>
            </h3>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Line type="monotone" dataKey="SAT-01_cpu" stroke="#06b6d4" strokeWidth={2} dot={false} name="SAT-01 CPU" />
                <Line type="monotone" dataKey="SAT-02_cpu" stroke="#a855f7" strokeWidth={2} dot={false} name="SAT-02 CPU" />
                <Line type="monotone" dataKey="SAT-03_cpu" stroke="#10b981" strokeWidth={2} dot={false} name="SAT-03 CPU" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
