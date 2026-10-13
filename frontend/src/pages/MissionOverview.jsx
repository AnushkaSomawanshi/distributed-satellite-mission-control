import React, { useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity, AlertTriangle, ArrowUpRight, BatteryCharging, CheckCircle2,
  ChevronRight, CircleDot, Clock3, Cpu, Gauge, Globe2, Layers3, Radio,
  Satellite, Signal, Thermometer, Wifi, Zap
} from 'lucide-react';

const earthImage = 'https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?auto=format&fit=crop&w=1600&q=90';

const healthyStates = ['HEALTHY', 'ONLINE', 'OPERATIONAL', 'CONNECTED'];
const warningStates = ['WARNING', 'DEGRADED', 'SUSPECTED'];
const criticalStates = ['OFFLINE', 'DISCONNECTED', 'CRITICAL'];

function display(value, suffix = '') {
  return value === undefined || value === null || value === '' ? '—' : `${value}${suffix}`;
}

function stateKind(status) {
  const value = String(status || 'UNKNOWN').toUpperCase();
  if (healthyStates.includes(value)) return 'good';
  if (warningStates.includes(value)) return 'warning';
  if (criticalStates.includes(value)) return 'bad';
  return 'unknown';
}

function StateBadge({ status }) {
  const kind = stateKind(status);
  return <span className={`orbit-state orbit-state--${kind}`}><span />{String(status || 'UNKNOWN').replaceAll('_', ' ')}</span>;
}

function PanelHeading({ icon: Icon, title, subtitle, action }) {
  return <div className="orbit-pro-panel-heading">
    <div className="flex min-w-0 items-center gap-3">
      <div className="orbit-pro-heading-icon"><Icon size={16} /></div>
      <div className="min-w-0"><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>
    </div>
    {action}
  </div>;
}

function MetricCard({ icon: Icon, label, value, detail, tone = 'cyan' }) {
  return <div className="orbit-pro-metric">
    <div className={`orbit-pro-metric-icon orbit-tone--${tone}`}><Icon size={17} /></div>
    <div className="min-w-0 flex-1">
      <p className="orbit-pro-eyebrow">{label}</p>
      <div className="orbit-pro-metric-value">{value}</div>
      <p className="orbit-pro-metric-detail">{detail}</p>
    </div>
    <span className="orbit-pro-metric-accent" />
  </div>;
}

export default function MissionOverview({ satellites = [], observatoryStats = {}, onSelectSatellite }) {
  const [selectedId, setSelectedId] = useState('');
  const [view, setView] = useState('Fleet');
  const fleet = useMemo(
    () => [...satellites].sort((a, b) => String(a.satellite_id).localeCompare(String(b.satellite_id))),
    [satellites]
  );
  const selected = fleet.find(s => s.satellite_id === selectedId) || fleet[0];
  const healthy = fleet.filter(s => healthyStates.includes(String(s.status || '').toUpperCase())).length;
  const warnings = fleet.filter(s => warningStates.includes(String(s.status || '').toUpperCase())).length;
  const critical = fleet.filter(s => criticalStates.includes(String(s.status || '').toUpperCase())).length;
  const connected = Boolean(observatoryStats?.websocket?.connected ?? observatoryStats?.websocket?.is_connected);
  const streamRate = observatoryStats?.websocket?.messages_per_second;
  const brokerKnown = observatoryStats?.rabbitmq?.connected;
  const brokerConnected = brokerKnown === true;
  const heartbeatAges = fleet.map(s => Number(s.seconds_since_heartbeat)).filter(Number.isFinite);
  const freshestHeartbeat = heartbeatAges.length ? Math.min(...heartbeatAges) : null;
  const nowUtc = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

  const services = [
    { label: 'Mission Control API', detail: 'Backend service', state: Object.keys(observatoryStats || {}).length ? 'REPORTED' : 'UNKNOWN', icon: Layers3 },
    { label: 'Live event stream', detail: 'WebSocket connection', state: connected ? 'CONNECTED' : 'DISCONNECTED', icon: Wifi },
    { label: 'Message broker', detail: 'RabbitMQ service metrics', state: brokerKnown === undefined ? 'UNKNOWN' : brokerConnected ? 'CONNECTED' : 'DISCONNECTED', icon: Radio },
    { label: 'Satellite network', detail: `${fleet.length} registered node${fleet.length === 1 ? '' : 's'}`, state: fleet.length ? 'CONNECTED' : 'UNKNOWN', icon: Satellite }
  ];

  return <div className="orbit-dashboard orbit-pro-dashboard">
    <header className="orbit-pro-pagehead">
      <div>
        <div className="orbit-pro-kicker"><span /> ORBITTRACK <span className="orbit-pro-kicker-slash">/</span> FLEET OPERATIONS</div>
        <h1>Mission Control</h1>
        <p>Satellite constellation status, telemetry and distributed service health.</p>
      </div>
      <div className="orbit-pro-clock"><Clock3 size={14} /><span>{nowUtc}</span></div>
    </header>

    <section className="orbit-pro-metrics-grid" aria-label="Fleet summary">
      <MetricCard icon={Satellite} label="Registered satellites" value={fleet.length ? String(fleet.length).padStart(2, '0') : '—'} detail={fleet.length ? `${healthy} reporting healthy / online` : 'Waiting for node registration'} tone="cyan" />
      <MetricCard icon={Activity} label="Fleet availability" value={fleet.length ? `${Math.round((healthy / fleet.length) * 100)}%` : '—'} detail={fleet.length ? `${warnings} warning · ${critical} critical/offline` : 'No fleet state available'} tone={critical ? 'red' : 'green'} />
      <MetricCard icon={Radio} label="Telemetry throughput" value={streamRate == null ? '—' : Number(streamRate).toFixed(1)} detail={streamRate == null ? 'Message rate not reported by service' : 'messages per second'} tone="blue" />
      <MetricCard icon={Zap} label="Event stream" value={connected ? 'Connected' : 'Unconfirmed'} detail={connected ? 'WebSocket connection reported' : 'Awaiting connection confirmation'} tone={connected ? 'green' : 'amber'} />
    </section>

    <section className="orbit-pro-primary-grid">
      <article className="orbit-pro-panel orbit-pro-globe-panel">
        <PanelHeading icon={Globe2} title="Global fleet view" subtitle="Constellation overview · orbital overlays are illustrative" action={<div className="orbit-pro-tabs">{['Fleet', 'Coverage', 'Ground'].map(tab => <button key={tab} className={view === tab ? 'active' : ''} onClick={() => setView(tab)}>{tab}</button>)}</div>} />
        <div className="orbit-pro-globe-stage">
          <div className="orbit-pro-starfield" />
          <div className="orbit-pro-globe-glow" />
          <div className="orbit-pro-earth" style={{ backgroundImage: `url("${earthImage}")` }} />
          <svg className="orbit-pro-orbits" viewBox="0 0 900 480" preserveAspectRatio="none" aria-hidden="true">
            <ellipse cx="450" cy="240" rx="335" ry="104" transform="rotate(-24 450 240)" />
            <ellipse cx="450" cy="240" rx="300" ry="155" transform="rotate(32 450 240)" className="orbit-pro-orbit-muted" />
            <path d="M75 370 C205 130 465 90 810 205" className="orbit-pro-ground-path" />
            <path d="M470 38 C635 128 662 324 548 435" className="orbit-pro-orbit-dashed" />
            <circle cx="238" cy="159" r="4" /><circle cx="689" cy="302" r="4" /><circle cx="552" cy="112" r="3" /><circle cx="548" cy="435" r="4" />
          </svg>
          <div className="orbit-pro-globe-chip"><span className="orbit-pro-live-dot" /> {view === 'Fleet' ? 'FLEET VISUALIZATION' : view === 'Coverage' ? 'COVERAGE VIEW · ILLUSTRATIVE' : 'GROUND NETWORK · ILLUSTRATIVE'}</div>
          {selected && <button className="orbit-pro-satellite-callout" onClick={() => onSelectSatellite?.(selected)} title="Open selected satellite details">
            <div className="flex items-center gap-2"><Satellite size={15} /><strong>{selected.satellite_id}</strong><ArrowUpRight size={12} /></div>
            <div className="orbit-pro-callout-row"><span>Health</span><b>{display(selected.health_score, '%')}</b></div>
            <div className="orbit-pro-callout-row"><span>Battery</span><b>{display(selected.battery, '%')}</b></div>
            <div className="orbit-pro-callout-row"><span>State</span><b>{String(selected.status || 'UNKNOWN').toUpperCase()}</b></div>
          </button>}
          {!selected && <div className="orbit-pro-satellite-callout"><strong>Awaiting satellite data</strong><p>Registered nodes appear here when the backend reports them.</p></div>}
          <div className="orbit-pro-globe-legend"><span><i className="legend-cyan" /> Selected node</span><span><i className="legend-line" /> Illustrative orbit</span><span><i className="legend-muted" /> Earth reference</span></div>
          <div className="orbit-pro-globe-controls"><button aria-label="Select fleet view" onClick={() => setView('Fleet')}>＋</button><button aria-label="Select coverage view" onClick={() => setView('Coverage')}>−</button><button aria-label="Reset visualization" onClick={() => setView('Fleet')}>⌖</button></div>
        </div>
        <div className="orbit-pro-globe-footer">
          <div><span>FLEET NODES</span><strong>{fleet.length || '—'}</strong></div>
          <div><span>HEALTHY / ONLINE</span><strong className="text-emerald-300">{fleet.length ? healthy : '—'}</strong></div>
          <div><span>ATTENTION REQUIRED</span><strong className={warnings + critical ? 'text-amber-300' : ''}>{fleet.length ? warnings + critical : '—'}</strong></div>
          <div><span>FRESHEST HEARTBEAT</span><strong>{freshestHeartbeat === null ? '—' : `${freshestHeartbeat}s ago`}</strong></div>
        </div>
      </article>

      <div className="orbit-pro-side-stack">
        <article className="orbit-pro-panel">
          <PanelHeading icon={Gauge} title="Selected satellite" subtitle={selected ? `Latest values · ${selected.satellite_id}` : 'Live telemetry snapshot'} action={selected && <StateBadge status={selected.status} />} />
          {selected ? <div className="orbit-pro-telemetry-grid">
            <div className="orbit-pro-telemetry-cell"><div><BatteryCharging size={14} /><span>Battery</span></div><strong>{display(selected.battery, '%')}</strong><div className="orbit-pro-bar"><span style={{ width: `${Math.max(0, Math.min(100, Number(selected.battery) || 0))}%` }} /></div></div>
            <div className="orbit-pro-telemetry-cell"><div><Gauge size={14} /><span>Health score</span></div><strong>{display(selected.health_score, '%')}</strong><div className="orbit-pro-bar"><span style={{ width: `${Math.max(0, Math.min(100, Number(selected.health_score) || 0))}%` }} /></div></div>
            <div className="orbit-pro-telemetry-cell"><div><Thermometer size={14} /><span>Temperature</span></div><strong>{display(selected.temperature, '°C')}</strong><small>Latest reported value</small></div>
            <div className="orbit-pro-telemetry-cell"><div><Cpu size={14} /><span>CPU usage</span></div><strong>{display(selected.cpu_usage, '%')}</strong><small>Latest reported value</small></div>
          </div> : <div className="orbit-pro-empty">No satellite telemetry has been received yet.</div>}
          <div className="orbit-pro-panel-footer"><span>Source: Mission Control API</span><NavLink to="/telemetry">Inspect telemetry <ChevronRight size={13} /></NavLink></div>
        </article>

        <article className="orbit-pro-panel">
          <PanelHeading icon={Signal} title="Communications & services" subtitle="Reported connectivity indicators" action={<NavLink to="/observatory" className="orbit-pro-text-link">Details <ChevronRight size={12} /></NavLink>} />
          <div className="orbit-pro-service-list">
            {services.map(({ label, detail, state, icon: Icon }) => <div key={label} className="orbit-pro-service-row">
              <div className="orbit-pro-service-icon"><Icon size={15} /></div>
              <div className="min-w-0 flex-1"><strong>{label}</strong><span>{detail}</span></div>
              <StateBadge status={state} />
            </div>)}
          </div>
          <div className="orbit-pro-broker-note"><CircleDot size={12} /> Service indicators are shown only when reported; unknown does not mean healthy.</div>
        </article>
      </div>
    </section>

    <section className="orbit-pro-lower-grid">
      <article className="orbit-pro-panel orbit-pro-fleet-panel">
        <PanelHeading icon={Satellite} title="Satellite fleet" subtitle="Select a node to inspect its latest reported state" action={<NavLink to="/registry" className="orbit-pro-text-link">Full registry <ChevronRight size={12} /></NavLink>} />
        <div className="orbit-pro-table-wrap"><table className="orbit-pro-table">
          <thead><tr><th>Satellite node</th><th>State</th><th>Health</th><th>Battery</th><th>Heartbeat age</th><th /></tr></thead>
          <tbody>{fleet.map(s => <tr key={s.satellite_id} className={selected?.satellite_id === s.satellite_id ? 'selected' : ''} onClick={() => { setSelectedId(s.satellite_id); }}>
            <td><div className="orbit-pro-node-cell"><span><Satellite size={15} /></span><div><strong>{s.satellite_id}</strong><small>{s.node_id || 'Satellite node'}</small></div></div></td>
            <td><StateBadge status={s.status} /></td>
            <td>{display(s.health_score, '%')}</td>
            <td>{display(s.battery, '%')}</td>
            <td>{s.seconds_since_heartbeat == null ? '—' : `${s.seconds_since_heartbeat}s ago`}</td>
            <td><button className="orbit-pro-row-action" onClick={e => { e.stopPropagation(); setSelectedId(s.satellite_id); onSelectSatellite?.(s); }} aria-label={`Open ${s.satellite_id} details`}><ChevronRight size={15} /></button></td>
          </tr>)}</tbody>
        </table>
        {!fleet.length && <div className="orbit-pro-empty"><Satellite size={22} /><strong>No satellite nodes reporting</strong><span>Start the satellite services or check the backend connection.</span></div>}</div>
      </article>

      <article className="orbit-pro-panel orbit-pro-health-panel">
        <PanelHeading icon={Activity} title="Network status" subtitle="Current distributed-system indicators" />
        <div className="orbit-pro-health-summary"><div><span>Fleet state</span><strong>{fleet.length ? `${healthy} / ${fleet.length} healthy` : 'Awaiting data'}</strong></div><div className={critical ? 'orbit-pro-summary-alert' : ''}><span>Unavailable / critical</span><strong>{fleet.length ? critical : '—'}</strong></div></div>
        <div className="orbit-pro-health-bars">
          <div><div><span>Healthy / online</span><b>{fleet.length ? healthy : '—'}</b></div><div className="orbit-pro-stacked-bar"><span className="bar-good" style={{ width: `${fleet.length ? healthy / fleet.length * 100 : 0}%` }} /></div></div>
          <div><div><span>Warning / suspected</span><b>{fleet.length ? warnings : '—'}</b></div><div className="orbit-pro-stacked-bar"><span className="bar-warning" style={{ width: `${fleet.length ? warnings / fleet.length * 100 : 0}%` }} /></div></div>
          <div><div><span>Offline / critical</span><b>{fleet.length ? critical : '—'}</b></div><div className="orbit-pro-stacked-bar"><span className="bar-bad" style={{ width: `${fleet.length ? critical / fleet.length * 100 : 0}%` }} /></div></div>
        </div>
        <div className="orbit-pro-health-footer"><div className={connected ? 'is-good' : ''}><span className="orbit-pro-status-dot" /> WebSocket <b>{connected ? 'Connected' : 'Not confirmed'}</b></div><div className={brokerConnected ? 'is-good' : ''}><span className="orbit-pro-status-dot" /> RabbitMQ <b>{brokerKnown === undefined ? 'Unknown' : brokerConnected ? 'Connected' : 'Disconnected'}</b></div></div>
        <NavLink to="/faults" className="orbit-pro-recovery-link"><AlertTriangle size={14} /> Open fault controls <ChevronRight size={14} /></NavLink>
      </article>
    </section>

    <footer className="orbit-pro-footnote"><span><CheckCircle2 size={12} /> Live values are sourced from the connected backend.</span><span>Earth imagery and orbital paths are illustrative; this view does not calculate real satellite positions.</span></footer>
  </div>;
}
