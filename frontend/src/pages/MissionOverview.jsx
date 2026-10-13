import React, { useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, BatteryCharging,
  CheckCircle2, ChevronRight, CircleDot, Clock3, Cpu, Crosshair, Database,
  Gauge, Globe2, Layers3, Radio, RefreshCw, Satellite, Signal, Thermometer,
  Zap
} from 'lucide-react';

const earthImage = 'https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?auto=format&fit=crop&w=1600&q=90';

function formatValue(value, suffix = '') {
  return value === undefined || value === null || value === '' ? '—' : `${value}${suffix}`;
}

function StatusPill({ status }) {
  const value = String(status || 'UNKNOWN').toUpperCase();
  const style = ['HEALTHY', 'ONLINE', 'OPERATIONAL', 'CONNECTED'].includes(value)
    ? 'text-emerald-300 bg-emerald-400/10 border-emerald-400/20'
    : ['WARNING', 'DEGRADED', 'SUSPECTED'].includes(value)
      ? 'text-amber-300 bg-amber-400/10 border-amber-400/20'
      : ['OFFLINE', 'DISCONNECTED', 'CRITICAL'].includes(value)
        ? 'text-rose-300 bg-rose-400/10 border-rose-400/20'
        : 'text-slate-300 bg-slate-400/10 border-slate-400/20';
  return <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-semibold tracking-wide ${style}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{value}</span>;
}

function Metric({ icon: Icon, label, value, unit, tone = 'cyan', note }) {
  const tones = { cyan: 'text-cyan-300 bg-cyan-400/10', green: 'text-emerald-300 bg-emerald-400/10', amber: 'text-amber-300 bg-amber-400/10', blue: 'text-sky-300 bg-sky-400/10' };
  return <div className="orbit-metric">
    <div className={`orbit-metric-icon ${tones[tone] || tones.cyan}`}><Icon size={16} /></div>
    <div className="min-w-0 flex-1"><p className="text-[11px] text-slate-400">{label}</p><div className="mt-1 flex items-baseline gap-1"><strong className="text-xl font-semibold tracking-tight text-slate-100">{value}</strong>{unit && <span className="text-[10px] text-slate-500">{unit}</span>}</div>{note && <p className="mt-1 truncate text-[10px] text-slate-500">{note}</p>}</div>
  </div>;
}

export default function MissionOverview({ satellites = [], observatoryStats = {}, onSelectSatellite }) {
  const [selectedId, setSelectedId] = useState('');
  const [activeTab, setActiveTab] = useState('Fleet');
  const [imageLoaded, setImageLoaded] = useState(false);
  const fleet = useMemo(() => [...satellites].sort((a, b) => String(a.satellite_id).localeCompare(String(b.satellite_id))), [satellites]);
  const selected = fleet.find(s => s.satellite_id === selectedId) || fleet[0];
  const healthy = fleet.filter(s => ['HEALTHY', 'ONLINE', 'OPERATIONAL'].includes(String(s.status || '').toUpperCase())).length;
  const warnings = fleet.filter(s => ['WARNING', 'SUSPECTED'].includes(String(s.status || '').toUpperCase())).length;
  const critical = fleet.filter(s => ['OFFLINE', 'DISCONNECTED', 'CRITICAL'].includes(String(s.status || '').toUpperCase())).length;
  const connected = Boolean(observatoryStats?.websocket?.connected ?? observatoryStats?.websocket?.is_connected);
  const streamRate = observatoryStats?.websocket?.messages_per_second;
  const brokerConnected = Boolean(observatoryStats?.rabbitmq?.connected);
  const battery = selected?.battery;
  const health = selected?.health_score;

  return <div className="orbit-dashboard space-y-4 pb-8">
    <section className="flex flex-wrap items-end justify-between gap-3">
      <div><div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[.24em] text-cyan-300"><span className="h-px w-7 bg-cyan-400" /> Fleet operations / overview</div><h2 className="text-2xl font-semibold tracking-tight text-white md:text-3xl">Mission Control</h2><p className="mt-1 text-sm text-slate-400">Satellite fleet status, system telemetry and communications health.</p></div>
      <div className="flex items-center gap-2 rounded-lg border border-slate-700/70 bg-slate-950/60 px-3 py-2 text-xs text-slate-300"><Clock3 size={14} className="text-cyan-300" /><span>{new Date().toUTCString().replace(' GMT', ' UTC')}</span></div>
    </section>

    <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      <Metric icon={Satellite} label="Fleet availability" value={fleet.length ? `${healthy}/${fleet.length}` : '—'} unit="active" tone="green" note={fleet.length ? 'Reported satellite states' : 'Waiting for fleet data'} />
      <Metric icon={Activity} label="Telemetry stream" value={streamRate === undefined ? '—' : Number(streamRate).toFixed(1)} unit="msg/s" tone="cyan" note={connected ? 'WebSocket connected' : 'Stream state not confirmed'} />
      <Metric icon={Radio} label="Message broker" value={brokerConnected ? 'Connected' : 'Unknown'} tone={brokerConnected ? 'green' : 'amber'} note="Broker status from service metrics" />
      <Metric icon={AlertTriangle} label="Attention required" value={warnings + critical} unit="satellites" tone={warnings + critical ? 'amber' : 'blue'} note={`${warnings} warning · ${critical} unavailable/critical`} />
    </section>

    <section className="grid grid-cols-1 gap-4 2xl:grid-cols-[minmax(0,1.65fr)_minmax(360px,1fr)]">
      <div className="orbit-panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 px-4 py-3">
          <div className="flex items-center gap-3"><div className="rounded-lg border border-cyan-400/25 bg-cyan-400/10 p-2 text-cyan-300"><Globe2 size={18} /></div><div><h3 className="text-sm font-semibold text-slate-100">Global fleet view</h3><p className="text-[10px] text-slate-500">Earth visualization · operational overview</p></div></div>
          <div className="flex items-center gap-1 rounded-lg border border-slate-700/80 bg-slate-950/70 p-1">{['Fleet', 'Coverage', 'Ground'].map(tab => <button key={tab} onClick={() => setActiveTab(tab)} className={`rounded-md px-3 py-1.5 text-[11px] transition ${activeTab === tab ? 'bg-cyan-400/15 text-cyan-200' : 'text-slate-400 hover:text-white'}`}>{tab}</button>)}</div>
        </div>
        <div className="orbit-earth-stage">
          <div className="orbit-earth-stars" />
          <div className="orbit-earth-halo" />
          <div className={`orbit-earth-image ${imageLoaded ? 'is-loaded' : ''}`} style={{ backgroundImage: `url("${earthImage}")` }} />
          <svg className="orbit-earth-arcs" viewBox="0 0 900 460" preserveAspectRatio="none" aria-hidden="true">
            <ellipse cx="450" cy="230" rx="330" ry="104" transform="rotate(-22 450 230)" fill="none" stroke="rgba(34,211,238,.75)" strokeWidth="1.5" strokeDasharray="5 8" />
            <ellipse cx="450" cy="230" rx="290" ry="165" transform="rotate(31 450 230)" fill="none" stroke="rgba(56,189,248,.48)" strokeWidth="1.2" />
            <path d="M100 340 C250 100 510 80 790 180" fill="none" stroke="rgba(45,212,191,.75)" strokeWidth="1.6" />
            <circle cx="260" cy="165" r="4" fill="#67e8f9" /><circle cx="690" cy="265" r="4" fill="#67e8f9" /><circle cx="550" cy="115" r="3" fill="#a5f3fc" />
          </svg>
          <div className="orbit-map-label left-4 top-4"><span className="orbit-live-dot" /> {activeTab === 'Fleet' ? 'Fleet visualization' : activeTab === 'Coverage' ? 'Coverage view' : 'Ground network'}</div>
          <div className="orbit-map-label bottom-4 left-4"><span className="inline-block h-1.5 w-5 rounded-full bg-cyan-300" /> Orbital overlays are illustrative</div>
          {selected && <div className="orbit-selected-sat right-4 top-4"><div className="flex items-center gap-2"><Satellite size={16} className="text-cyan-300" /><span className="font-semibold text-white">{selected.satellite_id}</span></div><div className="mt-2 space-y-1 text-[10px] text-slate-400"><div className="flex justify-between gap-5"><span>Health</span><span className="text-slate-100">{formatValue(health, '%')}</span></div><div className="flex justify-between gap-5"><span>Battery</span><span className="text-slate-100">{formatValue(battery, '%')}</span></div><div className="flex justify-between gap-5"><span>State</span><span className="text-slate-100">{selected.status || 'Unknown'}</span></div></div></div>}
          {!selected && <div className="orbit-selected-sat right-4 top-4 text-xs text-slate-400">Waiting for satellite telemetry</div>}
          <div className="absolute bottom-4 right-4 flex flex-col gap-2"><button aria-label="Zoom in" className="orbit-map-control" onClick={() => setActiveTab('Coverage')}>＋</button><button aria-label="Reset view" className="orbit-map-control" onClick={() => setActiveTab('Fleet')}>⌖</button></div>
        </div>
        <div className="grid grid-cols-3 divide-x divide-slate-800/80 border-t border-slate-800/80">
          <div className="p-3"><p className="text-[10px] text-slate-500">Fleet nodes</p><p className="mt-1 text-lg font-semibold text-white">{fleet.length || '—'}</p></div>
          <div className="p-3"><p className="text-[10px] text-slate-500">Healthy / online</p><p className="mt-1 text-lg font-semibold text-emerald-300">{fleet.length ? healthy : '—'}</p></div>
          <div className="p-3"><p className="text-[10px] text-slate-500">Needs attention</p><p className="mt-1 text-lg font-semibold text-amber-300">{fleet.length ? warnings + critical : '—'}</p></div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="orbit-panel">
          <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3"><div><h3 className="text-sm font-semibold text-white">Selected satellite</h3><p className="mt-0.5 text-[10px] text-slate-500">Live values reported by the service</p></div>{selected && <StatusPill status={selected.status} />}</div>
          {selected ? <div className="grid grid-cols-2 gap-px bg-slate-800/70">
            <div className="bg-slate-950/80 p-4"><div className="flex items-center gap-2 text-[11px] text-slate-400"><BatteryCharging size={14} className="text-cyan-300" /> Battery</div><div className="mt-2 text-2xl font-semibold text-white">{formatValue(selected.battery, '%')}</div><div className="orbit-progress"><span style={{ width: `${Math.max(0, Math.min(100, Number(selected.battery) || 0))}%` }} /></div></div>
            <div className="bg-slate-950/80 p-4"><div className="flex items-center gap-2 text-[11px] text-slate-400"><Gauge size={14} className="text-cyan-300" /> Health score</div><div className="mt-2 text-2xl font-semibold text-white">{formatValue(selected.health_score, '%')}</div><div className="orbit-progress"><span style={{ width: `${Math.max(0, Math.min(100, Number(selected.health_score) || 0))}%` }} /></div></div>
            <div className="bg-slate-950/80 p-4"><div className="flex items-center gap-2 text-[11px] text-slate-400"><Thermometer size={14} className="text-cyan-300" /> Temperature</div><div className="mt-2 text-xl font-semibold text-white">{formatValue(selected.temperature, '°C')}</div><p className="mt-1 text-[10px] text-slate-500">Latest reported measurement</p></div>
            <div className="bg-slate-950/80 p-4"><div className="flex items-center gap-2 text-[11px] text-slate-400"><Cpu size={14} className="text-cyan-300" /> CPU usage</div><div className="mt-2 text-xl font-semibold text-white">{formatValue(selected.cpu_usage, '%')}</div><p className="mt-1 text-[10px] text-slate-500">Latest reported measurement</p></div>
          </div> : <div className="p-6 text-sm text-slate-400">No satellite telemetry has been received yet.</div>}
          <div className="flex items-center justify-between border-t border-slate-800/80 px-4 py-3"><span className="text-[10px] text-slate-500">Satellite record</span><NavLink to="/registry" className="flex items-center gap-1 text-[11px] text-cyan-300 hover:text-cyan-100">Open fleet <ChevronRight size={13} /></NavLink></div>
        </div>
        <div className="orbit-panel">
          <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3"><div><h3 className="text-sm font-semibold text-white">Platform services</h3><p className="text-[10px] text-slate-500">Connectivity indicators</p></div><Layers3 size={17} className="text-cyan-300" /></div>
          <div className="space-y-0 px-4">
            {[
              { label: 'Live event stream', detail: 'WebSocket channel', ok: connected },
              { label: 'Message broker', detail: 'RabbitMQ service', ok: brokerConnected },
              { label: 'Satellite fleet', detail: `${fleet.length} registered nodes`, ok: fleet.length > 0 }
            ].map(item => <div key={item.label} className="flex items-center justify-between gap-3 border-b border-slate-800/60 py-3 last:border-0"><div className="flex items-center gap-3"><div className={`rounded-lg p-2 ${item.ok ? 'bg-emerald-400/10 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}>{item.ok ? <CheckCircle2 size={15} /> : <CircleDot size={15} />}</div><div><p className="text-xs text-slate-200">{item.label}</p><p className="mt-0.5 text-[10px] text-slate-500">{item.detail}</p></div></div><StatusPill status={item.ok ? 'CONNECTED' : 'UNKNOWN'} /></div>)}
          </div>
        </div>
      </div>
    </section>

    <section className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <div className="orbit-panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 px-4 py-3"><div><h3 className="text-sm font-semibold text-white">Satellite fleet</h3><p className="text-[10px] text-slate-500">Select a node to inspect its latest reported state</p></div><NavLink to="/registry" className="text-[11px] text-cyan-300 hover:text-cyan-100">View all <ChevronRight size={13} className="inline" /></NavLink></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[560px] text-left text-xs"><thead className="bg-slate-900/70 text-[10px] uppercase tracking-wider text-slate-500"><tr><th className="px-4 py-3 font-medium">Satellite</th><th className="px-3 py-3 font-medium">Status</th><th className="px-3 py-3 font-medium">Health</th><th className="px-3 py-3 font-medium">Battery</th><th className="px-3 py-3 font-medium">Heartbeat</th></tr></thead><tbody className="divide-y divide-slate-800/60">{fleet.map(s => <tr key={s.satellite_id} onClick={() => { setSelectedId(s.satellite_id); onSelectSatellite?.(s); }} className={`cursor-pointer transition hover:bg-cyan-400/[.04] ${selected?.satellite_id === s.satellite_id ? 'bg-cyan-400/[.06]' : ''}`}><td className="px-4 py-3"><div className="flex items-center gap-2.5"><div className="rounded-md border border-cyan-400/20 bg-cyan-400/10 p-2 text-cyan-300"><Satellite size={14} /></div><div><p className="font-semibold text-slate-100">{s.satellite_id}</p><p className="mt-0.5 text-[10px] text-slate-500">{s.node_id || 'Satellite node'}</p></div></div></td><td className="px-3 py-3"><StatusPill status={s.status} /></td><td className="px-3 py-3 text-slate-200">{formatValue(s.health_score, '%')}</td><td className="px-3 py-3 text-slate-200">{formatValue(s.battery, '%')}</td><td className="px-3 py-3 text-slate-400">{s.seconds_since_heartbeat == null ? '—' : `${s.seconds_since_heartbeat}s ago`}</td></tr>)}</tbody></table>
        {fleet.length === 0 && <div className="px-4 py-10 text-center"><Satellite className="mx-auto mb-3 text-slate-600" size={24} /><p className="text-sm text-slate-300">No satellites are reporting</p><p className="mt-1 text-xs text-slate-500">Start the satellite services or check the backend connection.</p></div>}</div>
      </div>
      <div className="orbit-panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3"><div><h3 className="text-sm font-semibold text-white">Operations activity</h3><p className="text-[10px] text-slate-500">Derived from current service state</p></div><Activity size={16} className="text-cyan-300" /></div>
        <div className="space-y-0 px-4">{fleet.slice(0, 6).map((s, index) => <div key={s.satellite_id} className="flex items-start gap-3 border-b border-slate-800/60 py-3 last:border-0"><div className={`mt-0.5 rounded-full p-1.5 ${['HEALTHY','ONLINE','OPERATIONAL'].includes(String(s.status || '').toUpperCase()) ? 'bg-emerald-400/10 text-emerald-300' : 'bg-amber-400/10 text-amber-300'}`}>{['HEALTHY','ONLINE','OPERATIONAL'].includes(String(s.status || '').toUpperCase()) ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}</div><div className="min-w-0 flex-1"><p className="text-xs text-slate-200">{s.satellite_id} reported state: {s.status || 'UNKNOWN'}</p><p className="mt-1 text-[10px] text-slate-500">{s.seconds_since_heartbeat == null ? 'Heartbeat age unavailable' : `Last heartbeat ${s.seconds_since_heartbeat}s ago`}</p></div><span className="text-[10px] text-slate-600">#{String(index + 1).padStart(2, '0')}</span></div>)}
        {fleet.length === 0 && <div className="px-2 py-10 text-center text-xs text-slate-500">Operations activity will appear when nodes register.</div>}</div>
        <div className="border-t border-slate-800/80 px-4 py-3"><NavLink to="/runtime-observability" className="flex items-center justify-between text-[11px] text-cyan-300 hover:text-cyan-100">Open system event history <ChevronRight size={14} /></NavLink></div>
      </div>
    </section>
  </div>;
}
