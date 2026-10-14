import React, { useState } from 'react';
import { RadioTower, WifiOff } from 'lucide-react';
import { SATS, api, usePoll, useAction, PageHeader, Panel, Btn, Select, NumberInput, ErrorNote, Stat, fmtVector } from '../lib/fa2';

const tone = {
  GROUND_LOST: 'text-amber-300', GROUND_RESTORED: 'text-emerald-300', PEER_DEAD: 'text-rose-300',
  LEADER_ELECTED: 'text-cyan-300', TASK_REASSIGNED: 'text-violet-300', BERKELEY_DONE: 'text-sky-300', FAULT_CRASH: 'text-rose-400',
};

export default function BlackoutPage() {
  const [seconds, setSeconds] = useState(45);
  const [crash, setCrash] = useState('SAT-05');
  const [crashAfter, setCrashAfter] = useState(8);
  const [order, setOrder] = useState('lamport');
  const [status] = usePoll('/api/fa2/blackout/status', 1000);
  const [report, , reloadReport] = usePoll('/api/fa2/blackout/report', 3000);
  const { busy, error, run } = useAction();

  const active = status?.active;
  const left = active ? Math.max(0, Math.round(status.ends_at - status.now)) : 0;
  const timeline = (report?.timeline || []).slice().sort((a, b) => (order === 'lamport' ? (a.lamport - b.lamport) || a.node.localeCompare(b.node) : a.true_ts - b.true_ts));

  return (
    <div className="space-y-6">
      <PageHeader
        icon={RadioTower}
        title="Ground Blackout Mode"
        subtitle="Mission Control stops accepting satellite traffic. The satellites notice (3 failed heartbeats), keep coordinating on their own (beacons, election, task takeover, Berkeley without a time server) and buffer what they record. When contact returns they deliver everything and this page rebuilds the timeline in causal order."
      />

      <Panel title="Start a blackout" icon={WifiOff}>
        <div className="flex flex-wrap items-end gap-3">
          <NumberInput label="Duration (s)" value={seconds} onChange={setSeconds} width="w-20" />
          <Select label="Crash during it" value={crash} onChange={setCrash} options={[{ value: '', label: 'nobody' }, ...SATS]} />
          <NumberInput label="after (s)" value={crashAfter} onChange={setCrashAfter} width="w-16" />
          <Btn tone="danger" busy={busy === 'start'} disabled={active}
            onClick={() => run('start', () => api('/api/fa2/blackout/start', { method: 'POST', body: { seconds: Number(seconds), crash: crash || null, crash_after_s: Number(crashAfter) } }))}>
            Cut the ground link
          </Btn>
          <Btn tone="ghost" disabled={!active} busy={busy === 'stop'} onClick={() => run('stop', async () => { await api('/api/fa2/blackout/stop', { method: 'POST' }); reloadReport(); })}>Restore now</Btn>
          {crash && <Btn tone="ghost" busy={busy === 'recover'} onClick={() => run('recover', () => api('/api/fa2/faults/recover', { method: 'POST', body: { target: crash } }))}>Recover {crash}</Btn>}
        </div>
        <p className="text-[11px] text-slate-500">Simulated: Mission Control refuses heartbeats, telemetry, events and time requests. This console still reads the satellites directly, so you can watch them work alone.</p>
        <ErrorNote error={error} />
      </Panel>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Ground link" value={active ? 'CUT' : 'UP'} hint={active ? `${left}s left` : 'normal operation'} />
        <Stat label="Satellites in autonomous mode" value={Object.values(status?.satellites || {}).filter((s) => s.ground_ok === false).length} />
        <Stat label="Events waiting on board" value={Object.values(status?.satellites || {}).reduce((a, s) => a + (s.events_waiting || 0), 0)} />
        <Stat label="Leader" value={(() => { const l = Object.values(status?.satellites || {}).filter((s) => !s.silent && !s.unreachable).map((s) => s.leader); return l.length && new Set(l).size === 1 ? l[0] : 'no agreement'; })()} />
      </div>

      <Panel title="Satellites right now">
        <table className="w-full text-xs font-mono">
          <thead className="text-slate-500 text-left"><tr><th className="py-1 pr-3">Satellite</th><th className="pr-3">Ground</th><th className="pr-3">Leader / term</th><th className="pr-3">Tasks</th><th>Events buffered</th></tr></thead>
          <tbody className="text-slate-200">
            {SATS.map((s) => {
              const x = status?.satellites?.[s] || {};
              return (
                <tr key={s} className="border-t border-slate-800">
                  <td className="py-1.5 pr-3">{s}{x.silent ? <span className="text-rose-300"> (crashed)</span> : ''}</td>
                  <td className={`pr-3 ${x.ground_ok === false ? 'text-amber-300' : 'text-emerald-300'}`}>{x.unreachable ? 'unreachable' : x.ground_ok === false ? 'LOST — autonomous' : 'ok'}</td>
                  <td className="pr-3">{x.leader ?? '—'} / {x.term ?? '—'}</td>
                  <td className="pr-3">{(x.tasks || []).join(', ') || '—'}</td>
                  <td>{x.events_waiting ?? '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

      <Panel title="What happened while the ground was gone" right={<Select label="Order" value={order} onChange={setOrder} options={[{ value: 'lamport', label: 'Causal (Lamport)' }, { value: 'time', label: 'True time' }]} />}>
        {!report?.available ? <div className="text-xs text-slate-400">No blackout has run yet.</div> : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Stat label="Blackout length" value={`${report.window.seconds} s`} />
              <Stat label="Events during it" value={report.summary.events_during_blackout} hint={`${report.summary.delivered_only_after_ground_returned} delivered only after contact returned`} />
              <Stat label="Satellites declared dead" value={report.summary.satellites_declared_dead.join(', ') || 'none'} />
              <Stat label="Tasks moved / Berkeley rounds" value={`${report.summary.tasks_reassigned.length} / ${report.summary.berkeley_rounds}`} />
            </div>
            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-xs font-mono">
                <thead className="text-slate-500 text-left sticky top-0 bg-slate-950"><tr><th className="py-1 pr-3">Lamport</th><th className="pr-3">Time</th><th className="pr-3">Satellite</th><th className="pr-3">Event</th><th className="pr-3">Detail</th><th>Vector</th></tr></thead>
                <tbody className="text-slate-200">
                  {timeline.map((e, i) => (
                    <tr key={i} className="border-t border-slate-800">
                      <td className="py-1 pr-3">{e.lamport}</td>
                      <td className="pr-3">{new Date(e.true_ts * 1000).toLocaleTimeString()}</td>
                      <td className="pr-3">{e.node}</td>
                      <td className={`pr-3 ${tone[e.label] || ''}`}>{e.label}{e.reported_after_blackout ? ' ⧗' : ''}</td>
                      <td className="pr-3 text-slate-400">{e.detail ? Object.entries(e.detail).filter(([k]) => ['peer', 'leader', 'task_id', 'to', 'from', 'term', 'spread_after_ms', 'duration_s'].includes(k)).map(([k, v]) => `${k}=${v}`).join(' ') : ''}</td>
                      <td className="text-slate-500">{fmtVector(e.vector)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-slate-500">⧗ = recorded on board during the blackout and delivered after contact returned. Lamport order is consistent with happened-before; satellites' counters advance at different rates, so it is not wall-clock order.</p>
          </>
        )}
      </Panel>
    </div>
  );
}
