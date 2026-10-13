import React, { useState } from 'react';
import { Clock, RotateCcw, Satellite, Users } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell, CartesianGrid } from 'recharts';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, NumberInput, ErrorNote, Stat, fmtVector } from '../lib/fa2';

export default function ClockSyncPage() {
  const [target, setTarget] = useState('SAT-02');
  const [offset, setOffset] = useState(600);
  const [drift, setDrift] = useState(0);
  const [lastSync, setLastSync] = useState(null);
  const [data] = usePoll('/api/fa2/clocks', 1000);
  const { busy, error, run } = useAction();

  const clocks = data?.clocks || {};
  const rows = SATS.map((s) => ({ sat: s, skew: clocks[s]?.clock?.skew_ms ?? null, down: clocks[s]?.unreachable || clocks[s]?.silent }));
  const skews = rows.filter((r) => r.skew != null && !r.down).map((r) => r.skew);
  const spread = skews.length ? (Math.max(...skews) - Math.min(...skews)).toFixed(1) : null;
  const maxAbs = skews.length ? Math.max(...skews.map(Math.abs)).toFixed(1) : null;

  const sync = async (name, path) => {
    const res = await run(name, () => api(path, { method: 'POST' }));
    if (res) setLastSync(res);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Clock}
        title="Clock Synchronization"
        subtitle="Each satellite keeps its own clock. Inject drift, then synchronise with Cristian's algorithm (Mission Control as time server) or Berkeley (the elected leader averages the satellites' clocks, no server needed)."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Spread between clocks" value={spread != null ? `${spread} ms` : '—'} hint="max − min skew" />
        <Stat label="Largest |skew| vs true time" value={maxAbs != null ? `${maxAbs} ms` : '—'} />
        <Stat label="Satellites reporting" value={skews.length} />
        <Stat label="Last sync" value={lastSync ? lastSync.algorithm : '—'} hint={lastSync ? new Date(lastSync.at * 1000).toLocaleTimeString() : 'none yet'} />
      </div>

      <Panel title="Inject drift and synchronise" icon={RotateCcw}>
        <div className="flex flex-wrap items-end gap-3">
          <Select label="Satellite" value={target} onChange={setTarget} options={SATS} />
          <NumberInput label="Jump (ms)" value={offset} onChange={setOffset} width="w-24" />
          <NumberInput label="Drift (ppm)" value={drift} onChange={setDrift} width="w-24" />
          <Btn tone="ghost" busy={busy === 'drift'} onClick={() => run('drift', () => api('/api/fa2/faults/clock-drift', { method: 'POST', body: { target, offset_ms: Number(offset), drift_ppm: Number(drift) } }))}>
            Inject CLOCK_DRIFT
          </Btn>
          <Btn tone="ghost" busy={busy === 'reset'} onClick={() => run('reset', () => api('/api/fa2/faults/clock-reset', { method: 'POST', body: {} }))}>Reset all</Btn>
        </div>
        <div className="flex flex-wrap items-end gap-3 pt-2 border-t border-slate-800">
          <Btn busy={busy === 'cristian'} onClick={() => sync('cristian', '/api/fa2/clocks/cristian')}>
            <span className="inline-flex items-center gap-1"><Satellite className="w-3.5 h-3.5" />Run Cristian (every satellite)</span>
          </Btn>
          <Btn busy={busy === 'berkeley'} onClick={() => sync('berkeley', '/api/fa2/clocks/berkeley')}>
            <span className="inline-flex items-center gap-1"><Users className="w-3.5 h-3.5" />Run Berkeley (leader as daemon)</span>
          </Btn>
          <span className="text-[11px] text-slate-500">1000 ppm = 1 ms gained per second. Real crystals drift ~10–100 ppm; larger values make the demo visible.</span>
        </div>
        <ErrorNote error={error} />
      </Panel>

      <Panel title="Skew of each satellite's clock from true time (live)">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 10, right: 16, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="#1e293b" vertical={false} />
              <XAxis dataKey="sat" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={11} unit=" ms" width={70} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', fontSize: 12 }} formatter={(v) => [`${Number(v).toFixed(2)} ms`, 'skew']} />
              <ReferenceLine y={0} stroke="#64748b" />
              <Bar dataKey="skew" isAnimationActive={false} radius={[3, 3, 0, 0]}>
                {rows.map((r) => <Cell key={r.sat} fill={r.down ? '#475569' : Math.abs(r.skew || 0) > 50 ? '#f59e0b' : '#22d3ee'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-[11px] text-slate-500">True time = the host clock all processes share. The algorithms never read it; satellites report it only so the result can be checked.</p>
      </Panel>

      {lastSync && (
        <Panel title={`Last round: ${lastSync.algorithm === 'berkeley' ? `Berkeley, daemon ${lastSync.daemon}` : 'Cristian'}`}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Spread before" value={`${lastSync.spread_before_ms ?? '—'} ms`} />
            <Stat label="Spread after" value={`${lastSync.spread_after_ms ?? '—'} ms`} />
            <Stat label="Max |skew| before" value={`${lastSync.max_abs_skew_before_ms ?? '—'} ms`} />
            <Stat label="Max |skew| after" value={`${lastSync.max_abs_skew_after_ms ?? '—'} ms`} hint={lastSync.algorithm === 'berkeley' ? 'Berkeley aligns clocks to each other, not to true time' : undefined} />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead className="text-slate-500 text-left">
                <tr><th className="py-1 pr-3">Satellite</th><th className="pr-3">RTT</th>{lastSync.algorithm === 'berkeley' && <th className="pr-3">Offset from daemon</th>}<th className="pr-3">Adjustment</th><th className="pr-3">Skew before</th><th>Skew after</th></tr>
              </thead>
              <tbody className="text-slate-200">
                {(lastSync.nodes || []).map((n) => (
                  <tr key={n.node} className="border-t border-slate-800">
                    <td className="py-1.5 pr-3">{n.node}</td>
                    <td className="pr-3">{n.rtt_ms ?? '—'} ms</td>
                    {lastSync.algorithm === 'berkeley' && <td className="pr-3">{n.offset_from_leader_ms} ms</td>}
                    <td className="pr-3">{n.adjustment_ms ?? n.error ?? '—'}{n.adjustment_ms != null ? ' ms' : ''}</td>
                    <td className="pr-3">{n.skew_before_ms ?? '—'} ms</td>
                    <td>{n.skew_after_ms ?? '—'} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      <Panel title="Logical clocks (as each satellite holds them)">
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead className="text-slate-500 text-left">
              <tr><th className="py-1 pr-3">Satellite</th><th className="pr-3">Lamport</th><th className="pr-3">Vector [01..05]</th><th>Peer clock offsets from beacons</th></tr>
            </thead>
            <tbody className="text-slate-200">
              {SATS.map((s) => (
                <tr key={s} className="border-t border-slate-800">
                  <td className="py-1.5 pr-3">{s}</td>
                  <td className="pr-3">{clocks[s]?.lamport ?? '—'}</td>
                  <td className="pr-3">{clocks[s]?.vector ? fmtVector(clocks[s].vector) : '—'}</td>
                  <td className="text-slate-400">{Object.entries(clocks[s]?.peer_offsets_ms || {}).filter(([, v]) => v != null).map(([p, v]) => `${p} ${v > 0 ? '+' : ''}${Math.round(v)}`).join(' · ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-slate-500">Beacon offsets include the one-way network delay, so they are estimates; Berkeley and Cristian correct for delay with the measured round trip.</p>
      </Panel>
    </div>
  );
}
